"""CLI エントリポイントのテスト。"""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from timelapse.cli import app
from timelapse import __version__

runner = CliRunner()


def _ffprobe_video(path: Path) -> dict:
    """ffprobe で動画のストリーム情報を取得する。"""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "generate" in result.output


def test_generate_help() -> None:
    result = runner.invoke(app, ["generate", "--help"])
    assert result.exit_code == 0
    assert "--duration" in result.output
    assert "--fit" in result.output
    assert "--sort" in result.output


def test_generate_dry_run(sample_image_dir: Path) -> None:
    result = runner.invoke(app, ["generate", str(sample_image_dir), "--dry-run"])
    assert result.exit_code == 0


def test_generate_nonexistent_dir(tmp_path: Path) -> None:
    result = runner.invoke(app, ["generate", str(tmp_path / "no_such_dir")])
    assert result.exit_code == 1


def test_generate_empty_dir(tmp_path: Path) -> None:
    result = runner.invoke(app, ["generate", str(tmp_path)])
    assert result.exit_code == 1


def test_generate_calls_encode(sample_image_dir: Path, tmp_path: Path) -> None:
    output = tmp_path / "out.mp4"
    mock_encode = MagicMock(return_value=output)
    mock_normalize = MagicMock(return_value=[tmp_path / "000000.jpg"])

    with (
        patch("timelapse.cli.encode", mock_encode),
        patch("timelapse.cli.normalize_all", mock_normalize),
    ):
        result = runner.invoke(
            app,
            ["generate", str(sample_image_dir), "-o", str(output), "--duration", "0.5"],
        )

    assert result.exit_code == 0
    assert mock_encode.called
    call_kwargs = mock_encode.call_args.kwargs
    assert call_kwargs["duration_per_image"] == 0.5


# --- 統合テスト: 実際に FFmpeg を動かして出力を検証 ---

@pytest.mark.integration
def test_generate_integration_output_exists(sample_image_dir: Path, tmp_path: Path) -> None:
    """実際にエンコードして MP4 ファイルが生成されることを確認。"""
    output = tmp_path / "out.mp4"
    result = runner.invoke(
        app,
        ["generate", str(sample_image_dir), "-o", str(output), "--duration", "0.5"],
    )
    assert result.exit_code == 0, result.output
    assert output.exists()
    assert output.stat().st_size > 0


@pytest.mark.integration
def test_generate_integration_reels_spec(sample_image_dir: Path, tmp_path: Path) -> None:
    """出力動画が Reels 仕様 (解像度・コーデック) を満たすことを ffprobe で検証。"""
    from timelapse.reels_spec import REELS_WIDTH, REELS_HEIGHT

    output = tmp_path / "out.mp4"
    runner.invoke(
        app,
        ["generate", str(sample_image_dir), "-o", str(output), "--duration", "0.3"],
    )

    info = _ffprobe_video(output)
    streams = {s["codec_type"]: s for s in info["streams"]}

    video = streams["video"]
    assert video["codec_name"] == "h264"
    assert video["width"] == REELS_WIDTH
    assert video["height"] == REELS_HEIGHT


@pytest.mark.integration
def test_generate_integration_all_frames_present(sample_image_dir: Path, tmp_path: Path) -> None:
    """N枚の画像が全てフレームとして動画に含まれることを検証 (上書きバグの回帰テスト)。"""
    output = tmp_path / "out.mp4"
    duration_per = 0.5
    fps = 30.0

    result = runner.invoke(
        app,
        [
            "generate", str(sample_image_dir),
            "-o", str(output),
            "--duration", str(duration_per),
            "--fps", str(fps),
        ],
    )
    assert result.exit_code == 0, result.output

    info = _ffprobe_video(output)
    video_stream = next(s for s in info["streams"] if s["codec_type"] == "video")

    # sample_image_dir には 3 枚の画像がある (conftest 参照)
    # 3枚 × 0.5秒 × 30fps = 45フレーム以上が期待される
    n_images = 3
    expected_min_frames = int(n_images * duration_per * fps * 0.9)  # 10% の誤差を許容
    actual_frames = int(video_stream["nb_frames"])
    assert actual_frames >= expected_min_frames, (
        f"フレーム数が少なすぎます: {actual_frames} < {expected_min_frames}。"
        "画像が上書きされている可能性があります。"
    )
