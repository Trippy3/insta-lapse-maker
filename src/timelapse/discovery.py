"""画像ファイルの列挙・ソートモジュール。"""

import re
import warnings
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from pathlib import Path
from typing import Optional

from PIL import Image
from PIL.ExifTags import Base

from .errors import NoImagesFoundError

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".bmp", ".tiff", ".tif"}


class SortOrder(str, Enum):
    FILENAME = "filename"
    EXIF_DATETIME = "exif"


def _extract_exif_datetime(path: Path) -> Optional[str]:
    try:
        with Image.open(path) as img:
            if value := img.getexif().get(Base.DateTimeOriginal):
                return str(value)
    except Exception:
        pass
    return None


def _natural_sort_key(path: Path) -> list:
    parts = re.split(r"(\d+)", path.stem)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def discover_images(
    directory: Path,
    sort_order: SortOrder = SortOrder.FILENAME,
    recursive: bool = False,
) -> list[Path]:
    """
    ディレクトリから対応画像を収集してソートして返す。

    EXIF ソート時に日時が取得できない画像はファイル名でフォールバックし、
    末尾に並べる。recursive=True でサブディレクトリも対象にする。
    """
    if not directory.is_dir():
        raise NotADirectoryError(f"ディレクトリが見つかりません: {directory}")

    if recursive:
        all_paths = directory.rglob("*")
    else:
        all_paths = directory.iterdir()
    images = [p for p in all_paths if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]

    if not images:
        raise NoImagesFoundError(
            f"{directory} に対応する画像ファイルが見つかりません。\n"
            f"対応形式: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if sort_order == SortOrder.FILENAME:
        return sorted(images, key=_natural_sort_key)

    with ThreadPoolExecutor() as executor:
        datetimes = list(executor.map(_extract_exif_datetime, images))

    dated = [(dt, img) for dt, img in zip(datetimes, images) if dt]
    undated = [img for dt, img in zip(datetimes, images) if not dt]

    if undated:
        warnings.warn(
            f"EXIF 日時が取得できなかった画像をファイル名順で末尾に追加します: {[p.name for p in undated]}",
            stacklevel=2,
        )

    dated.sort(key=lambda x: x[0])
    return [p for _, p in dated] + sorted(undated, key=_natural_sort_key)
