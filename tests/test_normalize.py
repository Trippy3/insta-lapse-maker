"""normalize モジュールのテスト。"""

from pathlib import Path

import pytest
from PIL import Image

from timelapse.normalize import FitMode, normalize_all, normalize_image
from timelapse.reels_spec import REELS_HEIGHT, REELS_WIDTH


def test_normalize_pad_portrait(single_image: Path, tmp_path: Path) -> None:
    dst = tmp_path / "out.jpg"
    normalize_image(single_image, dst, fit_mode=FitMode.PAD)
    with Image.open(dst) as img:
        assert img.size == (REELS_WIDTH, REELS_HEIGHT)


def test_normalize_crop_portrait(single_image: Path, tmp_path: Path) -> None:
    dst = tmp_path / "out.jpg"
    normalize_image(single_image, dst, fit_mode=FitMode.CROP)
    with Image.open(dst) as img:
        assert img.size == (REELS_WIDTH, REELS_HEIGHT)


def test_normalize_wide_image_pad(tmp_path: Path) -> None:
    """横長画像を pad モードで変換してもサイズが正しいことを確認。"""
    src = tmp_path / "wide.jpg"
    Image.new("RGB", (1920, 1080), (100, 200, 100)).save(src)
    dst = tmp_path / "out.jpg"
    normalize_image(src, dst, fit_mode=FitMode.PAD)
    with Image.open(dst) as img:
        assert img.size == (REELS_WIDTH, REELS_HEIGHT)


def test_normalize_pad_color(single_image: Path, tmp_path: Path) -> None:
    """pad カラーが反映されることを確認 (角ピクセルを確認)。JPEG 圧縮で±2の誤差を許容。"""
    dst = tmp_path / "out.jpg"
    pad_color = (128, 0, 128)
    normalize_image(single_image, dst, fit_mode=FitMode.PAD, pad_color=pad_color)
    with Image.open(dst) as img:
        pixel = img.getpixel((0, 0))
        for actual, expected in zip(pixel, pad_color):
            assert abs(actual - expected) <= 2


def test_normalize_all_output_count(sample_image_dir: Path, tmp_path: Path) -> None:
    from timelapse.discovery import discover_images
    images = discover_images(sample_image_dir)
    normalized = normalize_all(images, tmp_path / "frames")
    assert len(normalized) == 3
    for p in normalized:
        assert p.exists()
        with Image.open(p) as img:
            assert img.size == (REELS_WIDTH, REELS_HEIGHT)


def test_normalize_all_sequential_naming(sample_image_dir: Path, tmp_path: Path) -> None:
    from timelapse.discovery import discover_images
    images = discover_images(sample_image_dir)
    normalized = normalize_all(images, tmp_path / "frames")
    for i, p in enumerate(normalized):
        assert p.name == f"{i:06d}.jpg"


def test_normalize_all_unique_files(sample_image_dir: Path, tmp_path: Path) -> None:
    """N枚の入力に対して N個の異なるパスが生成されることを検証 (上書きバグの回帰テスト)。"""
    from timelapse.discovery import discover_images
    images = discover_images(sample_image_dir)
    normalized = normalize_all(images, tmp_path / "frames")
    assert len(normalized) == len(images)
    assert len(set(normalized)) == len(images), "正規化後のパスに重複があります (上書きが発生している)。"


def test_normalize_all_distinct_content(sample_image_dir: Path, tmp_path: Path) -> None:
    """入力画像が異なる色なら出力ファイルの内容も異なることを検証。"""
    from timelapse.discovery import discover_images
    import hashlib

    images = discover_images(sample_image_dir)
    normalized = normalize_all(images, tmp_path / "frames")

    hashes = [hashlib.md5(p.read_bytes()).hexdigest() for p in normalized]
    assert len(set(hashes)) == len(hashes), "異なる入力画像が同一ファイルに上書きされています。"
