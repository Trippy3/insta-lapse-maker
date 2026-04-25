"""system モジュールのテスト。"""

import subprocess
from unittest.mock import patch, MagicMock

import pytest

from timelapse.errors import FFmpegNotFoundError, FFmpegVersionError
from timelapse.system import check_ffmpeg, find_ffmpeg, get_ffmpeg_version


def test_find_ffmpeg_returns_path() -> None:
    with patch("timelapse.system.shutil.which", return_value="/usr/bin/ffmpeg"):
        path = find_ffmpeg()
    assert path == "/usr/bin/ffmpeg"


def test_find_ffmpeg_raises_when_not_found() -> None:
    with patch("timelapse.system.shutil.which", return_value=None):
        with pytest.raises(FFmpegNotFoundError):
            find_ffmpeg()


def test_get_ffmpeg_version_parses_output() -> None:
    mock_result = MagicMock()
    mock_result.stdout = "ffmpeg version 6.1.1 Copyright ..."
    with (
        patch("timelapse.system.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("timelapse.system.subprocess.run", return_value=mock_result),
    ):
        major, minor = get_ffmpeg_version()
    assert major == 6
    assert minor == 1


def test_check_ffmpeg_raises_on_old_version() -> None:
    mock_result = MagicMock()
    mock_result.stdout = "ffmpeg version 3.4.0"
    with (
        patch("timelapse.system.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("timelapse.system.subprocess.run", return_value=mock_result),
    ):
        with pytest.raises(FFmpegVersionError):
            check_ffmpeg(min_version=(4, 0))


def test_check_ffmpeg_passes_on_valid_version() -> None:
    mock_result = MagicMock()
    mock_result.stdout = "ffmpeg version 6.0.0"
    with (
        patch("timelapse.system.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("timelapse.system.subprocess.run", return_value=mock_result),
    ):
        path = check_ffmpeg()
    assert path == "/usr/bin/ffmpeg"
