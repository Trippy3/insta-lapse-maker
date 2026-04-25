"""ソース画像サムネイル生成 (HEIC → JPEG 変換含む)。"""

from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageOps

try:
    import pillow_heif  # type: ignore

    pillow_heif.register_heif_opener()
except Exception:  # pragma: no cover - 実運用では常にインストール済み
    pass

THUMB_MAX = 512


def _path_fingerprint(src: Path) -> str:
    """画像パス + mtime + size から一意なサムネイルキーを作る。"""
    st = src.stat()
    raw = f"{src.resolve()}|{st.st_mtime_ns}|{st.st_size}".encode()
    return hashlib.sha1(raw).hexdigest()[:16]


def thumbnail_path(cache_root: Path, src: Path) -> Path:
    key = _path_fingerprint(src)
    return cache_root / "thumbs" / f"{key}.jpg"


def ensure_thumbnail(src: Path, cache_root: Path) -> Path:
    """サムネイルを生成 (キャッシュ済みなら再利用) し、パスを返す。"""
    dst = thumbnail_path(cache_root, src)
    if dst.is_file():
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as img:
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        img.thumbnail((THUMB_MAX, THUMB_MAX), Image.LANCZOS)
        img.save(dst, format="JPEG", quality=85, optimize=True)
    return dst


def image_dimensions(src: Path) -> tuple[int, int]:
    """EXIF 回転適用後の (width, height) を返す。"""
    with Image.open(src) as img:
        img = ImageOps.exif_transpose(img)
        return img.size
