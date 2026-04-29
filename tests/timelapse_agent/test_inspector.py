"""inspector.py のユニットテスト。"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from timelapse_agent.inspector import ImageInfo, inspect_directory


def _make_jpeg(path: Path, width: int, height: int) -> None:
    img = Image.new("RGB", (width, height), color=(128, 64, 32))
    img.save(path, "JPEG")


def test_inspect_directory_returns_metadata(tmp_path: Path) -> None:
    _make_jpeg(tmp_path / "img_01.jpg", 1200, 900)
    _make_jpeg(tmp_path / "img_02.jpg", 800, 1200)

    result = inspect_directory(tmp_path)

    assert len(result) == 2
    assert result[0]["filename"] == "img_01.jpg"
    assert result[0]["width"] == 1200
    assert result[0]["height"] == 900
    assert result[0]["aspect_ratio"] == pytest.approx(1200 / 900, abs=1e-3)
    assert result[0]["exif_datetime"] is None
    assert result[0]["file_size_bytes"] > 0


def test_inspect_directory_returns_typed_fields(tmp_path: Path) -> None:
    _make_jpeg(tmp_path / "a.jpg", 100, 100)
    result = inspect_directory(tmp_path)
    info = result[0]
    # TypedDict のキーが揃っていることを確認
    expected_keys = set(ImageInfo.__annotations__)
    assert expected_keys == set(info.keys())


def test_inspect_directory_filename_sort(tmp_path: Path) -> None:
    for name in ("c.jpg", "a.jpg", "b.jpg"):
        _make_jpeg(tmp_path / name, 100, 100)
    result = inspect_directory(tmp_path)
    assert [r["filename"] for r in result] == ["a.jpg", "b.jpg", "c.jpg"]


def test_inspect_directory_raises_on_nonexistent(tmp_path: Path) -> None:
    with pytest.raises(NotADirectoryError):
        inspect_directory(tmp_path / "nonexistent")


def test_inspect_directory_raises_when_no_images(tmp_path: Path) -> None:
    from timelapse.errors import NoImagesFoundError
    (tmp_path / "readme.txt").write_text("hello")
    with pytest.raises(NoImagesFoundError):
        inspect_directory(tmp_path)
