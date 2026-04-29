"""画像ディレクトリを探索し、各ファイルのメタデータを返す。"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from PIL import Image
from PIL.ExifTags import Base

from timelapse.discovery import SortOrder, discover_images


class ImageInfo(TypedDict):
    path: str
    filename: str
    width: int
    height: int
    aspect_ratio: float
    exif_datetime: str | None
    file_size_bytes: int


def inspect_directory(
    directory: Path,
    sort_order: SortOrder = SortOrder.FILENAME,
    recursive: bool = False,
) -> list[ImageInfo]:
    """ディレクトリ内の画像を探索し、メタデータのリストを返す。"""
    images = discover_images(directory, sort_order=sort_order, recursive=recursive)
    return [_get_image_info(p) for p in images]


def _get_image_info(path: Path) -> ImageInfo:
    exif_dt: str | None = None
    width = 0
    height = 0
    try:
        with Image.open(path) as img:
            width, height = img.size
            if exif := img.getexif():
                if dt := exif.get(Base.DateTimeOriginal):
                    exif_dt = str(dt)
    except Exception:
        pass
    aspect_ratio = round(width / height, 4) if height else 0.0
    return ImageInfo(
        path=str(path),
        filename=path.name,
        width=width,
        height=height,
        aspect_ratio=aspect_ratio,
        exif_datetime=exif_dt,
        file_size_bytes=path.stat().st_size,
    )
