"""メディア API: ディレクトリ走査、サムネイル配信、画像メタ取得。"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from timelapse.discovery import SUPPORTED_EXTENSIONS, SortOrder, discover_images
from timelapse.errors import NoImagesFoundError

from ..config import AppConfig
from ..services.thumbnail import ensure_thumbnail, image_dimensions, thumbnail_path
from .deps import get_config

router = APIRouter(prefix="/api/media", tags=["media"])


class ImageInfo(BaseModel):
    path: str
    width: int
    height: int
    filename: str


class ScanResponse(BaseModel):
    directory: str
    images: list[ImageInfo]


@router.get("/scan", response_model=ScanResponse)
def scan_directory(
    directory: Annotated[str, Query(description="画像ディレクトリの絶対パス")],
    sort: SortOrder = SortOrder.FILENAME,
    recursive: bool = False,
) -> ScanResponse:
    resolved = Path(directory).expanduser()
    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"ディレクトリが見つかりません: {resolved}")
    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail=f"ディレクトリではありません: {resolved}")

    try:
        paths = discover_images(resolved, sort, recursive)
    except NoImagesFoundError:
        # UI 側で「0 件」と表示できるよう空リストを返す (エラー扱いしない)
        paths = []

    items: list[ImageInfo] = []
    for p in paths:
        try:
            w, h = image_dimensions(p)
        except Exception:  # pragma: no cover - 壊れた画像
            continue
        items.append(ImageInfo(path=str(p), width=w, height=h, filename=p.name))
    return ScanResponse(directory=str(resolved.resolve()), images=items)


@router.get("/thumbnail")
def get_thumbnail(
    path: Annotated[str, Query()],
    config: Annotated[AppConfig, Depends(get_config)],
) -> FileResponse:
    src = Path(path).expanduser()
    if not src.is_file():
        raise HTTPException(status_code=404, detail="画像が見つかりません")
    if src.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="未対応の拡張子")
    thumb = ensure_thumbnail(src, config.cache_root)
    return FileResponse(thumb, media_type="image/jpeg")


@router.get("/info", response_model=ImageInfo)
def get_info(path: Annotated[str, Query()]) -> ImageInfo:
    src = Path(path).expanduser()
    if not src.is_file():
        raise HTTPException(status_code=404, detail="画像が見つかりません")
    w, h = image_dimensions(src)
    return ImageInfo(path=str(src), width=w, height=h, filename=src.name)
