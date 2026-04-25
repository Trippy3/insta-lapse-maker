"""pytest 共通フィクスチャ。"""

import io
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw


def _make_test_image(path: Path, width: int = 400, height: int = 300, color: tuple = (255, 0, 0)) -> Path:
    img = Image.new("RGB", (width, height), color)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="JPEG")
    return path


def _make_structured_image(path: Path, bg_color: tuple = (200, 100, 50), size: int = 128) -> Path:
    """pHashテスト用の構造を持つ画像を生成する。"""
    img = Image.new("RGB", (size, size), bg_color)
    draw = ImageDraw.Draw(img)
    draw.line([(0, size // 2), (size, size // 2)], fill=(255, 255, 255), width=6)
    draw.line([(size // 2, 0), (size // 2, size)], fill=(255, 255, 255), width=6)
    draw.ellipse([size // 4, size // 4, 3 * size // 4, 3 * size // 4], outline=(0, 0, 0), width=4)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG")
    return path


def _make_noise_image(path: Path, seed: int = 42, size: int = 128) -> Path:
    """完全に異なる画像（ランダムノイズ）を生成する。"""
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, (size, size, 3), dtype=np.uint8)
    img = Image.fromarray(arr)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG")
    return path


@pytest.fixture()
def sample_image_dir(tmp_path: Path) -> Path:
    """3枚のテスト用 JPEG 画像が入ったディレクトリを返す。"""
    img_dir = tmp_path / "images"
    img_dir.mkdir()
    _make_test_image(img_dir / "001.jpg", color=(255, 0, 0))
    _make_test_image(img_dir / "002.jpg", color=(0, 255, 0))
    _make_test_image(img_dir / "003.jpg", color=(0, 0, 255))
    return img_dir


@pytest.fixture()
def single_image(tmp_path: Path) -> Path:
    return _make_test_image(tmp_path / "test.jpg")


@pytest.fixture()
def similarity_fixture(tmp_path: Path):
    """類似画像検索テスト用フィクスチャ。reference・similar（別ファイルだが同一コピー）・unrelated を返す。"""
    ref_dir = tmp_path / "similar_test"
    ref_dir.mkdir()

    reference = _make_structured_image(ref_dir / "reference.png", bg_color=(200, 100, 50))
    similar = ref_dir / "similar.png"
    # 同じ画像をコピー → pHash距離は0
    Image.open(reference).save(similar, format="PNG")

    unrelated = _make_noise_image(ref_dir / "unrelated.png", seed=42)

    search_dir = tmp_path / "search"
    search_dir.mkdir()
    Image.open(similar).save(search_dir / "similar.png", format="PNG")
    Image.open(unrelated).save(search_dir / "unrelated.png", format="PNG")

    return {
        "reference": reference,
        "similar": search_dir / "similar.png",
        "unrelated": search_dir / "unrelated.png",
        "search_dir": search_dir,
    }
