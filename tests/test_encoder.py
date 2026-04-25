"""encoder モジュールのテスト (FFmpeg 呼び出しはモック化)。"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from timelapse.encoder import _write_concat_list, build_ffmpeg_args, encode
from timelapse.errors import EncodingError
from timelapse.reels_spec import REELS_FPS, REELS_HEIGHT, REELS_WIDTH


def _make_images(tmp_path: Path, n: int = 3) -> list[Path]:
    imgs = []
    for i in range(n):
        p = tmp_path / f"{i:06d}.jpg"
        Image.new("RGB", (REELS_WIDTH, REELS_HEIGHT)).save(p)
        imgs.append(p)
    return imgs


def test_build_ffmpeg_args_contains_codec(tmp_path: Path) -> None:
    images = _make_images(tmp_path)
    concat_path = tmp_path / "list.txt"
    concat_path.write_text("")
    args = build_ffmpeg_args(images, tmp_path / "out.mp4", concat_list_path=concat_path)
    assert "libx264" in args
    assert "aac" in args
    assert "+faststart" in args


def test_build_ffmpeg_args_resolution(tmp_path: Path) -> None:
    images = _make_images(tmp_path)
    concat_path = tmp_path / "list.txt"
    concat_path.write_text("")
    args = build_ffmpeg_args(images, tmp_path / "out.mp4", concat_list_path=concat_path)
    assert f"scale={REELS_WIDTH}:{REELS_HEIGHT}" in args


def test_build_ffmpeg_args_inputs_before_output_options(tmp_path: Path) -> None:
    """全 -i 入力が出力オプション (-c:v 等) より前に並んでいることを検証。"""
    images = _make_images(tmp_path)
    concat_path = tmp_path / "list.txt"
    concat_path.write_text("")
    args = build_ffmpeg_args(images, tmp_path / "out.mp4", concat_list_path=concat_path)

    last_input_idx = max(i for i, a in enumerate(args) if a == "-i")
    first_codec_idx = next(i for i, a in enumerate(args) if a == "-c:v")
    assert last_input_idx < first_codec_idx, (
        "全入力 (-i) は出力オプション (-c:v) より前になければなりません。"
        f" last -i at {last_input_idx}, -c:v at {first_codec_idx}"
    )


def test_build_ffmpeg_args_anullsrc_is_input(tmp_path: Path) -> None:
    """anullsrc が -i フラグで入力として指定されていることを検証。"""
    images = _make_images(tmp_path)
    concat_path = tmp_path / "list.txt"
    concat_path.write_text("")
    args = build_ffmpeg_args(images, tmp_path / "out.mp4", concat_list_path=concat_path)

    anullsrc_idx = next((i for i, a in enumerate(args) if "anullsrc" in a), None)
    assert anullsrc_idx is not None
    assert args[anullsrc_idx - 1] == "-i", "anullsrc の直前は -i でなければなりません。"


def test_write_concat_list(tmp_path: Path) -> None:
    images = _make_images(tmp_path)
    list_path = tmp_path / "list.txt"
    _write_concat_list(images, 0.5, list_path)
    content = list_path.read_text()
    assert "duration 0.500000" in content
    assert str(images[0].resolve()) in content


def test_encode_dry_run_returns_output(tmp_path: Path) -> None:
    images = _make_images(tmp_path)
    output = tmp_path / "out.mp4"
    result = encode(images, output, dry_run=True)
    assert result == output
    assert not output.exists()


def test_encode_calls_ffmpeg(tmp_path: Path) -> None:
    images = _make_images(tmp_path)
    output = tmp_path / "out.mp4"

    mock_result = MagicMock()
    mock_result.returncode = 0

    with (
        patch("timelapse.encoder.check_ffmpeg", return_value="ffmpeg"),
        patch("timelapse.encoder.subprocess.run", return_value=mock_result) as mock_run,
    ):
        encode(images, output)

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert call_args[0] == "ffmpeg"
    assert str(output) in call_args


def test_encode_raises_on_ffmpeg_error(tmp_path: Path) -> None:
    images = _make_images(tmp_path)
    output = tmp_path / "out.mp4"

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "some error"

    with (
        patch("timelapse.encoder.check_ffmpeg", return_value="ffmpeg"),
        patch("timelapse.encoder.subprocess.run", return_value=mock_result),
    ):
        with pytest.raises(EncodingError):
            encode(images, output)


def test_encode_empty_images_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        encode([], tmp_path / "out.mp4")
