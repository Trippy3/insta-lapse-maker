"""画像類似度計算モジュール。"""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

import imagehash
import numpy as np
from PIL import Image, ImageOps

from .errors import InvalidImageError, ReferenceImageNotFoundError

try:
    import pillow_heif  # type: ignore[import-untyped]
    pillow_heif.register_heif_opener()
except ImportError:
    pass

DEFAULT_HASH_THRESHOLD = 10
DEFAULT_HISTOGRAM_THRESHOLD = 0.85
_HASH_BITS = 64  # 8x8 hash = 64 bits


class SimilarityStrategy(str, Enum):
    PHASH = "phash"
    DHASH = "dhash"
    AHASH = "ahash"
    HISTOGRAM = "histogram"
    COMBINED = "combined"


@dataclass(frozen=True)
class SimilarityResult:
    path: Path
    score: float
    distance: Optional[int]


class HashCache:
    """画像ハッシュの永続キャッシュ。mtime+sizeで無効化判定する。"""

    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "timelapse"
        self._cache_file = cache_dir / "hashes.json"
        self._data: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        if self._cache_file.exists():
            try:
                self._data = json.loads(self._cache_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def get(self, path: Path, strategy: SimilarityStrategy) -> Optional[imagehash.ImageHash]:
        key = str(path.resolve())
        with self._lock:
            entry = self._data.get(key)
        if entry is None:
            return None
        try:
            stat = path.stat()
        except OSError:
            return None
        if entry.get("mtime") != stat.st_mtime or entry.get("size") != stat.st_size:
            return None
        hash_str = entry.get(strategy.value)
        if hash_str is None:
            return None
        return imagehash.hex_to_hash(hash_str)

    def set(self, path: Path, strategy: SimilarityStrategy, hash_val: imagehash.ImageHash) -> None:
        key = str(path.resolve())
        try:
            stat = path.stat()
        except OSError:
            return
        with self._lock:
            entry = self._data.setdefault(key, {})
            entry["mtime"] = stat.st_mtime
            entry["size"] = stat.st_size
            entry[strategy.value] = str(hash_val)

    def save(self) -> None:
        self._cache_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._cache_file.with_suffix(".tmp")
        with self._lock:
            data_snapshot = json.dumps(self._data, indent=2, ensure_ascii=False)
        tmp.write_text(data_snapshot, encoding="utf-8")
        tmp.rename(self._cache_file)


def _open_image(path: Path) -> Image.Image:
    try:
        img = Image.open(path)
        return ImageOps.exif_transpose(img)
    except Exception as e:
        raise InvalidImageError(f"画像を開けません: {path}") from e


_HASH_FN_MAP: dict[SimilarityStrategy, Callable] = {
    SimilarityStrategy.PHASH: imagehash.phash,
    SimilarityStrategy.DHASH: imagehash.dhash,
    SimilarityStrategy.AHASH: imagehash.average_hash,
    SimilarityStrategy.COMBINED: imagehash.phash,
}


def compute_hash(path: Path, strategy: SimilarityStrategy) -> imagehash.ImageHash:
    """画像の知覚ハッシュを計算する（EXIF回転補正適用済み）。"""
    if strategy == SimilarityStrategy.HISTOGRAM:
        raise ValueError("HISTOGRAM戦略にはcompute_hash()は使用できません")
    img = _open_image(path)
    return _HASH_FN_MAP[strategy](img)


def _get_or_compute_hash(
    path: Path,
    strategy: SimilarityStrategy,
    cache: Optional[HashCache],
) -> imagehash.ImageHash:
    if cache is not None:
        cached = cache.get(path, strategy)
        if cached is not None:
            return cached
    h = compute_hash(path, strategy)
    if cache is not None:
        cache.set(path, strategy, h)
    return h


def compute_histogram_correlation(path_a: Path, path_b: Path) -> float:
    """2枚の画像のヒストグラム相関係数を返す (0.0~1.0)。"""
    img_a = _open_image(path_a).convert("RGB")
    img_b = _open_image(path_b).convert("RGB")
    hist_a = np.array(img_a.histogram(), dtype=float)
    hist_b = np.array(img_b.histogram(), dtype=float)
    hist_a /= hist_a.sum() + 1e-10
    hist_b /= hist_b.sum() + 1e-10
    corr = float(np.corrcoef(hist_a, hist_b)[0, 1])
    return max(0.0, corr)


def find_similar_images(
    reference: Path,
    candidates: list[Path],
    strategy: SimilarityStrategy = SimilarityStrategy.PHASH,
    threshold: int = DEFAULT_HASH_THRESHOLD,
    histogram_threshold: float = DEFAULT_HISTOGRAM_THRESHOLD,
    max_workers: Optional[int] = None,
    cache: Optional[HashCache] = None,
    on_progress: Optional[Callable[[int], None]] = None,
) -> list[SimilarityResult]:
    """
    基準画像に類似した候補画像を返す。

    壊れた画像は警告なしにスキップする。
    """
    if not reference.exists():
        raise ReferenceImageNotFoundError(f"基準画像が見つかりません: {reference}")

    if strategy == SimilarityStrategy.HISTOGRAM:
        results: list[SimilarityResult] = []
        for i, path in enumerate(candidates):
            try:
                corr = compute_histogram_correlation(reference, path)
                if corr >= histogram_threshold:
                    results.append(SimilarityResult(path=path, score=corr, distance=None))
            except (InvalidImageError, Exception):
                pass
            if on_progress:
                on_progress(i + 1)
        if cache is not None:
            cache.save()
        return results

    ref_hash = _get_or_compute_hash(reference, strategy, cache)

    def process(path: Path) -> Optional[SimilarityResult]:
        try:
            h = _get_or_compute_hash(path, strategy, cache)
            distance = int(ref_hash - h)
            if strategy == SimilarityStrategy.COMBINED:
                try:
                    corr = compute_histogram_correlation(reference, path)
                    if corr < histogram_threshold:
                        return None
                except (InvalidImageError, Exception):
                    return None
            if distance <= threshold:
                score = 1.0 - distance / _HASH_BITS
                return SimilarityResult(path=path, score=score, distance=distance)
            return None
        except (InvalidImageError, Exception):
            return None

    found: list[SimilarityResult] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process, p): p for p in candidates}
        completed = 0
        for future in as_completed(futures):
            completed += 1
            if on_progress:
                on_progress(completed)
            result = future.result()
            if result is not None:
                found.append(result)

    if cache is not None:
        cache.save()

    return found
