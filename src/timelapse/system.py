"""FFmpeg の存在確認・バージョン検出ユーティリティ。"""

import re
import shutil
import subprocess
from functools import lru_cache
from typing import Optional

from .errors import FFmpegNotFoundError, FFmpegVersionError

_MIN_VERSION = (4, 0)


def find_ffmpeg() -> str:
    """ffmpeg の実行パスを返す。見つからなければ FFmpegNotFoundError。"""
    path = shutil.which("ffmpeg")
    if path is None:
        raise FFmpegNotFoundError(
            "ffmpeg が見つかりません。インストールしてください。\n"
            "  Ubuntu/Debian: sudo apt install ffmpeg\n"
            "  macOS:         brew install ffmpeg"
        )
    return path


def get_ffmpeg_version(ffmpeg_path: Optional[str] = None) -> tuple[int, int]:
    """ffmpeg のバージョン (major, minor) を返す。"""
    path = ffmpeg_path or find_ffmpeg()
    result = subprocess.run(
        [path, "-version"],
        capture_output=True,
        text=True,
        check=False,
    )
    match = re.search(r"ffmpeg version (\d+)\.(\d+)", result.stdout)
    if not match:
        raise FFmpegVersionError(f"ffmpeg バージョンを取得できませんでした: {result.stdout[:200]}")
    return int(match.group(1)), int(match.group(2))


@lru_cache(maxsize=None)
def check_ffmpeg(min_version: tuple[int, int] = _MIN_VERSION) -> str:
    path = find_ffmpeg()
    major, minor = get_ffmpeg_version(path)
    if (major, minor) < min_version:
        raise FFmpegVersionError(
            f"ffmpeg {major}.{minor} は古すぎます。"
            f"{min_version[0]}.{min_version[1]} 以上が必要です。"
        )
    return path


def find_ffprobe() -> str:
    """ffprobe の実行パスを返す。見つからなければ FFmpegNotFoundError。"""
    path = shutil.which("ffprobe")
    if path is None:
        raise FFmpegNotFoundError("ffprobe が見つかりません。ffmpeg と一緒にインストールされるはずです。")
    return path
