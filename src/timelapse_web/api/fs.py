"""ファイルシステム走査 API。

UI の DirectoryPicker / OutputPicker から呼ばれる。セキュリティ上、許可ルート
(既定はユーザーホーム、`TIMELAPSE_WEB_FS_ROOTS` で上書き) 配下のみを公開する。
シンボリックリンクは解決後に再度ルート内判定を行う。
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from timelapse.discovery import SUPPORTED_EXTENSIONS

from ..config import AppConfig
from ..services.native_picker import (
    NativePickerUnavailable,
    PickRequest,
    active_backend as native_active_backend,
    is_available as native_is_available,
    pick as native_pick,
    unavailable_reason as native_unavailable_reason,
)
from .deps import get_config

router = APIRouter(prefix="/api/fs", tags=["fs"])

EntryType = Literal["dir", "image", "file", "other"]

# 直下に画像があるかチェックする際の走査上限 (大きなディレクトリで遅くならないよう)
_IMAGE_SCAN_HINT_LIMIT = 200


class FsEntry(BaseModel):
    name: str
    path: str
    type: EntryType
    has_images: bool = False


class HomeResponse(BaseModel):
    home: str
    roots: list[str]


class BrowseResponse(BaseModel):
    path: str
    parent: str | None
    entries: list[FsEntry]
    roots: list[str]


class NativePickMode(str):
    DIRECTORY = "directory"
    SAVE_FILE = "save-file"
    OPEN_FILE = "open-file"


class NativePickBody(BaseModel):
    mode: Literal["directory", "save-file", "open-file"]
    initial_dir: str | None = None
    initial_file: str | None = None
    title: str | None = None
    default_extension: str | None = Field(
        default=None,
        description="save-file 用。ユーザーが拡張子を省略した場合に補う",
    )
    filetype_name: str | None = None
    filetype_pattern: str | None = None


class NativePickResponse(BaseModel):
    path: str | None
    cancelled: bool = False


def _is_within_roots(path: Path, roots: tuple[Path, ...]) -> bool:
    for root in roots:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _resolve_within_roots(raw: str, roots: tuple[Path, ...]) -> Path:
    try:
        resolved = Path(raw).expanduser().resolve()
    except (OSError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=f"パスを解決できません: {exc}") from exc
    if not _is_within_roots(resolved, roots):
        raise HTTPException(
            status_code=403,
            detail=f"許可されたルートの外のパスです: {resolved}",
        )
    return resolved


def _has_images_hint(directory: Path) -> bool:
    """直下に画像が 1 枚でもあるか (上限付きで走査)。"""
    try:
        it = directory.iterdir()
    except (PermissionError, OSError):
        return False
    for i, entry in enumerate(it):
        if i >= _IMAGE_SCAN_HINT_LIMIT:
            break
        try:
            if entry.is_file() and entry.suffix.lower() in SUPPORTED_EXTENSIONS:
                return True
        except OSError:
            continue
    return False


def _classify(entry: Path, extra_suffixes: tuple[str, ...] = ()) -> EntryType:
    try:
        if entry.is_dir():
            return "dir"
        if entry.is_file():
            name_lower = entry.name.lower()
            if entry.suffix.lower() in SUPPORTED_EXTENSIONS:
                return "image"
            # 複合拡張子 (.tlproj.json など) も許可するため endswith で判定
            for suf in extra_suffixes:
                if name_lower.endswith(suf):
                    return "file"
    except OSError:
        return "other"
    return "other"


def _normalize_match_ext(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    out: list[str] = []
    for part in raw.split(","):
        p = part.strip().lower()
        if not p:
            continue
        if not p.startswith("."):
            p = "." + p
        out.append(p)
    return tuple(out)


def _parent_within_roots(path: Path, roots: tuple[Path, ...]) -> str | None:
    """path の親が許可ルート内に収まっていれば返す、さもなくば None。"""
    parent = path.parent
    if parent == path:
        return None
    if _is_within_roots(parent, roots):
        return str(parent)
    return None


@router.get("/home", response_model=HomeResponse)
def get_home(config: Annotated[AppConfig, Depends(get_config)]) -> HomeResponse:
    roots = config.effective_fs_roots()
    home = Path.home().resolve()
    # ホームが許可ルート内に無ければ最初のルートを既定として返す
    default = home if _is_within_roots(home, roots) else roots[0]
    return HomeResponse(home=str(default), roots=[str(r) for r in roots])


@router.get("/browse", response_model=BrowseResponse)
def browse_directory(
    path: Annotated[str, Query(description="走査対象の絶対パス")],
    config: Annotated[AppConfig, Depends(get_config)],
    show_hidden: bool = False,
    match_ext: Annotated[
        str | None,
        Query(description="画像以外で表示したい拡張子 (カンマ区切り、例: '.tlproj.json,.json')"),
    ] = None,
) -> BrowseResponse:
    roots = config.effective_fs_roots()
    resolved = _resolve_within_roots(path, roots)

    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"パスが見つかりません: {resolved}")
    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail=f"ディレクトリではありません: {resolved}")

    extra = _normalize_match_ext(match_ext)
    entries: list[FsEntry] = []
    try:
        iterator = sorted(resolved.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="このディレクトリは読み取れません") from exc
    for child in iterator:
        if not show_hidden and child.name.startswith("."):
            continue
        kind = _classify(child, extra)
        if kind == "other":
            # ディレクトリでも画像でもないファイルは省く (UI の見通しを良くする)
            continue
        has_images = kind == "dir" and _has_images_hint(child)
        entries.append(
            FsEntry(
                name=child.name,
                path=str(child),
                type=kind,
                has_images=has_images,
            )
        )

    return BrowseResponse(
        path=str(resolved),
        parent=_parent_within_roots(resolved, roots),
        entries=entries,
        roots=[str(r) for r in roots],
    )


@router.get("/native-available")
def get_native_available() -> dict:
    """ネイティブダイアログがこのサーバで利用可能かを返す (UI のヒント用)。

    利用できない場合は reason に人間可読な説明を載せる (トースト等で表示できる)。
    backend にはどのバックエンド (zenity / tkinter) が選ばれるかを返す。
    """
    reason = native_unavailable_reason()
    return {
        "available": reason is None,
        "reason": reason,
        "backend": native_active_backend(),
    }


@router.post("/native-pick", response_model=NativePickResponse)
def native_pick_endpoint(
    body: Annotated[NativePickBody, Body()],
    config: Annotated[AppConfig, Depends(get_config)],
) -> NativePickResponse:
    """OS ネイティブのダイアログでパスを選択する。利用不可時は 501。"""
    try:
        result = native_pick(
            PickRequest(
                mode=body.mode,
                initial_dir=body.initial_dir,
                initial_file=body.initial_file,
                title=body.title,
                default_extension=body.default_extension,
                filetype_name=body.filetype_name,
                filetype_pattern=body.filetype_pattern,
            )
        )
    except NativePickerUnavailable as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc

    if result is None:
        return NativePickResponse(path=None, cancelled=True)

    # 既存の fs_roots 制約と一致させるため、選択パスもルート内にあることを確認する
    roots = config.effective_fs_roots()
    try:
        resolved = Path(result).expanduser().resolve()
    except (OSError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=f"パスを解決できません: {exc}") from exc
    if not _is_within_roots(resolved, roots):
        raise HTTPException(
            status_code=403,
            detail=f"許可されたルートの外のパスは扱えません: {resolved}",
        )
    return NativePickResponse(path=str(resolved), cancelled=False)
