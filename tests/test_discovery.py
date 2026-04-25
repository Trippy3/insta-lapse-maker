"""discovery モジュールのテスト。"""

import pytest
from pathlib import Path
from PIL import Image

from timelapse.discovery import SortOrder, discover_images
from timelapse.errors import NoImagesFoundError


def test_discover_basic(sample_image_dir: Path) -> None:
    images = discover_images(sample_image_dir)
    assert len(images) == 3
    assert all(p.suffix.lower() == ".jpg" for p in images)


def test_discover_filename_sort(sample_image_dir: Path) -> None:
    images = discover_images(sample_image_dir, sort_order=SortOrder.FILENAME)
    names = [p.name for p in images]
    assert names == sorted(names)


def test_discover_natural_sort(tmp_path: Path) -> None:
    """自然順ソートで img9 が img10 より前に来ることを確認。"""
    for name in ("img10.jpg", "img2.jpg", "img9.jpg"):
        Image.new("RGB", (10, 10)).save(tmp_path / name)
    images = discover_images(tmp_path, sort_order=SortOrder.FILENAME)
    assert [p.name for p in images] == ["img2.jpg", "img9.jpg", "img10.jpg"]


def test_discover_no_images_raises(tmp_path: Path) -> None:
    with pytest.raises(NoImagesFoundError):
        discover_images(tmp_path)


def test_discover_not_a_directory(tmp_path: Path) -> None:
    with pytest.raises(NotADirectoryError):
        discover_images(tmp_path / "nonexistent")


def test_discover_ignores_non_image_files(tmp_path: Path) -> None:
    Image.new("RGB", (10, 10)).save(tmp_path / "photo.jpg")
    (tmp_path / "readme.txt").write_text("hello")
    (tmp_path / "data.csv").write_text("a,b")
    images = discover_images(tmp_path)
    assert len(images) == 1
    assert images[0].name == "photo.jpg"


def test_discover_exif_sort_fallback(sample_image_dir: Path) -> None:
    """EXIF なし画像がファイル名順フォールバックで末尾に来ることを確認。"""
    import warnings
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        images = discover_images(sample_image_dir, sort_order=SortOrder.EXIF_DATETIME)
    assert len(images) == 3
