"""画像を Reels 解像度 (1080x1920) に正規化するモジュール。"""

from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from pathlib import Path

from PIL import Image, ImageOps

from .reels_spec import REELS_HEIGHT, REELS_WIDTH

_TARGET_SIZE = (REELS_WIDTH, REELS_HEIGHT)


class FitMode(str, Enum):
    PAD = "pad"
    CROP = "crop"


def normalize_image(
    src: Path,
    dst: Path,
    fit_mode: FitMode = FitMode.PAD,
    pad_color: tuple[int, int, int] = (0, 0, 0),
) -> Path:
    with Image.open(src) as img:
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        if fit_mode == FitMode.PAD:
            result = ImageOps.pad(img, _TARGET_SIZE, method=Image.LANCZOS, color=pad_color)
        else:
            result = ImageOps.fit(img, _TARGET_SIZE, method=Image.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    result.save(dst, format="JPEG", quality=95)
    return dst


def normalize_all(
    images: list[Path],
    output_dir: Path,
    fit_mode: FitMode = FitMode.PAD,
    pad_color: tuple[int, int, int] = (0, 0, 0),
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    dsts = [output_dir / f"{i:06d}.jpg" for i in range(len(images))]
    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(normalize_image, src, dst, fit_mode, pad_color)
            for src, dst in zip(images, dsts)
        ]
        for f in futures:
            f.result()
    return dsts
