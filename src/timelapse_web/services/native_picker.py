"""OS ネイティブのファイルダイアログを呼び出すサービス。

バックエンドを複数持ち、環境で動くものを順に試す:
  1. **zenity** (Linux の GNOME/GTK 系。Wayland ネイティブでも動く)
  2. **tkinter** (subprocess として起動。macOS/Windows でも動く)

利用できない場合は NativePickerUnavailable を送出し、API 層で 501 に
フォールバックさせる。
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class NativePickerUnavailable(RuntimeError):
    """ネイティブダイアログが現環境で使えないことを表す。

    受け手は 501 Not Implemented 相当の応答に変換し、UI 側でフォールバックする。
    """


@dataclass(frozen=True)
class PickRequest:
    mode: str  # "directory" | "save-file" | "open-file"
    initial_dir: str | None = None
    initial_file: str | None = None
    title: str | None = None
    default_extension: str | None = None
    filetype_name: str | None = None
    filetype_pattern: str | None = None


# --- 環境判定 ---


def _has_display() -> bool:
    """Linux/BSD 上で DISPLAY もしくは WAYLAND_DISPLAY が set されているか。"""
    if sys.platform.startswith("linux") or sys.platform.startswith("freebsd"):
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    # macOS/Windows は常に GUI あり扱い
    return True


def _zenity_available() -> bool:
    if sys.platform != "linux" and not sys.platform.startswith("freebsd"):
        return False
    if not _has_display():
        return False
    return shutil.which("zenity") is not None


def _tkinter_available() -> bool:
    if not _has_display():
        return False
    try:
        import tkinter  # noqa: F401
    except Exception:
        return False
    return True


def unavailable_reason() -> str | None:
    """利用できない理由を返す。利用可能なら None。"""
    if not _has_display():
        return (
            "DISPLAY/WAYLAND_DISPLAY が未設定です "
            "(サーバを GUI セッション付きの端末から起動してください)"
        )
    if _zenity_available() or _tkinter_available():
        return None
    if sys.platform.startswith("linux"):
        return (
            "Linux 用の GUI ダイアログバックエンドが見つかりません "
            "(zenity を入れるか、python3-tk を導入してください)"
        )
    return "利用可能な GUI ダイアログバックエンドが見つかりません"


def is_available() -> bool:
    return unavailable_reason() is None


def active_backend() -> str | None:
    """現在優先されるバックエンド名 (診断用)。"""
    if _zenity_available():
        return "zenity"
    if _tkinter_available():
        return "tkinter"
    return None


# --- zenity バックエンド ---


def _zenity_pick(req: PickRequest, timeout_s: float) -> str | None:
    cmd: list[str] = ["zenity", "--file-selection"]
    if req.mode == "directory":
        cmd.append("--directory")
    elif req.mode == "save-file":
        cmd += ["--save", "--confirm-overwrite"]
    # open-file はデフォルト

    if req.title:
        cmd.append(f"--title={req.title}")

    # 初期パス (zenity は --filename= に path+filename を一括で渡す)
    initial = _compose_initial_path(req)
    if initial:
        cmd.append(f"--filename={initial}")

    # ファイルタイプフィルタ (save-file / open-file のみ意味あり)
    if req.mode != "directory" and req.filetype_pattern:
        name = req.filetype_name or req.filetype_pattern
        cmd.append(f"--file-filter={name} | {req.filetype_pattern}")
        cmd.append("--file-filter=All files | *")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except FileNotFoundError as exc:
        raise NativePickerUnavailable(f"zenity を起動できません: {exc}") from exc
    except subprocess.TimeoutExpired:
        return None

    # zenity: 0 = 選択 / 1 = キャンセル / その他 = エラー
    if proc.returncode == 0:
        picked = proc.stdout.strip()
        picked = _apply_default_extension(picked, req)
        return picked or None
    if proc.returncode == 1:
        return None
    detail = proc.stderr.strip() or f"zenity exited {proc.returncode}"
    raise NativePickerUnavailable(detail)


def _compose_initial_path(req: PickRequest) -> str | None:
    if req.mode == "directory":
        if req.initial_dir:
            return _ensure_trailing_slash(req.initial_dir)
        return None
    # file 系: ディレクトリ + ファイル名
    if req.initial_dir and req.initial_file:
        base = _ensure_trailing_slash(req.initial_dir)
        return base + req.initial_file
    if req.initial_dir:
        return _ensure_trailing_slash(req.initial_dir)
    if req.initial_file:
        return req.initial_file
    return None


def _ensure_trailing_slash(path: str) -> str:
    return path if path.endswith("/") else path + "/"


def _apply_default_extension(picked: str, req: PickRequest) -> str:
    """save-file モードで、ユーザーが拡張子を省いた場合に default_extension を補う。"""
    if req.mode != "save-file" or not picked or not req.default_extension:
        return picked
    ext = req.default_extension
    if not ext.startswith("."):
        ext = "." + ext
    if picked.lower().endswith(ext.lower()):
        return picked
    # 複合拡張子 (.tlproj.json) の場合は最後の .json だけ見て帰結判定しない
    return picked + ext


# --- tkinter バックエンド (subprocess 経由) ---


def _tkinter_pick(req: PickRequest, timeout_s: float) -> str | None:
    cmd: list[str] = [
        sys.executable,
        "-m",
        "timelapse_web.services._native_picker_worker",
        "--mode",
        req.mode,
    ]
    if req.initial_dir:
        cmd += ["--initial-dir", req.initial_dir]
    if req.initial_file:
        cmd += ["--initial-file", req.initial_file]
    if req.title:
        cmd += ["--title", req.title]
    if req.default_extension:
        cmd += ["--default-ext", req.default_extension]
    if req.filetype_name:
        cmd += ["--filetype-name", req.filetype_name]
    if req.filetype_pattern:
        cmd += ["--filetype-pattern", req.filetype_pattern]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except FileNotFoundError as exc:
        raise NativePickerUnavailable(f"Python インタプリタが起動できません: {exc}") from exc
    except subprocess.TimeoutExpired:
        return None

    if proc.returncode != 0:
        detail = proc.stderr.strip() or "tkinter worker failed"
        raise NativePickerUnavailable(detail)

    raw = proc.stdout.strip()
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise NativePickerUnavailable(f"tkinter worker の出力が不正です: {raw!r}") from exc
    picked = payload.get("path")
    return picked if isinstance(picked, str) and picked else None


# --- 公開 API ---


def pick(req: PickRequest, timeout_s: float = 300.0) -> str | None:
    """優先順位の高いバックエンドを順に試してダイアログを開く。"""
    reason = unavailable_reason()
    if reason is not None:
        raise NativePickerUnavailable(reason)

    errors: list[str] = []
    # 1. zenity
    if _zenity_available():
        try:
            return _zenity_pick(req, timeout_s)
        except NativePickerUnavailable as exc:
            errors.append(f"zenity: {exc}")
            logger.warning("zenity バックエンドが失敗: %s", exc)

    # 2. tkinter
    if _tkinter_available():
        try:
            return _tkinter_pick(req, timeout_s)
        except NativePickerUnavailable as exc:
            errors.append(f"tkinter: {exc}")
            logger.warning("tkinter バックエンドが失敗: %s", exc)

    raise NativePickerUnavailable(
        "すべてのネイティブダイアログバックエンドが失敗しました: " + " / ".join(errors)
        if errors
        else "利用可能なバックエンドがありません"
    )
