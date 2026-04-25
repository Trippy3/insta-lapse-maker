"""FFmpeg を使って正規化済み画像列から動画を生成するモジュール。"""

import subprocess
import tempfile
from pathlib import Path

from .errors import EncodingError
from .reels_spec import (
    AUDIO_BITRATE,
    AUDIO_CHANNELS,
    AUDIO_CODEC,
    AUDIO_SAMPLE_RATE,
    MOVFLAGS,
    REELS_FPS,
    REELS_HEIGHT,
    REELS_WIDTH,
    VIDEO_BITRATE,
    VIDEO_BUFSIZE,
    VIDEO_CODEC,
    VIDEO_GOP_SEC,
    VIDEO_LEVEL,
    VIDEO_MAX_B_FRAMES,
    VIDEO_MAXRATE,
    VIDEO_PIX_FMT,
    VIDEO_PROFILE,
)
from .system import check_ffmpeg


def build_ffmpeg_args(
    images: list[Path],
    output: Path,
    fps: float = REELS_FPS,
    duration_per_image: float = 0.3,
    ffmpeg_path: str = "ffmpeg",
    concat_list_path: Path | None = None,
) -> list[str]:
    """FFmpeg コマンド引数リストを生成する (実行しない)。"""
    gop = int(fps * VIDEO_GOP_SEC)

    if concat_list_path is not None:
        input_args = ["-f", "concat", "-safe", "0", "-i", str(concat_list_path)]
    else:
        if not images:
            raise ValueError("images が空です。")
        pattern = str(images[0].parent / "%06d.jpg")
        input_args = ["-framerate", str(fps), "-i", pattern]

    # 全入力を先に並べ、その後に出力オプションを置く (FFmpeg の要件)
    return [
        ffmpeg_path,
        "-y",
        *input_args,
        "-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate={AUDIO_SAMPLE_RATE}",
        "-c:v", VIDEO_CODEC,
        "-profile:v", VIDEO_PROFILE,
        "-level:v", VIDEO_LEVEL,
        "-b:v", VIDEO_BITRATE,
        "-maxrate", VIDEO_MAXRATE,
        "-bufsize", VIDEO_BUFSIZE,
        "-g", str(gop),
        "-bf", str(VIDEO_MAX_B_FRAMES),
        "-pix_fmt", VIDEO_PIX_FMT,
        "-vf", f"scale={REELS_WIDTH}:{REELS_HEIGHT}",
        "-c:a", AUDIO_CODEC,
        "-b:a", AUDIO_BITRATE,
        "-ac", str(AUDIO_CHANNELS),
        "-ar", str(AUDIO_SAMPLE_RATE),
        "-shortest",
        "-movflags", MOVFLAGS,
        str(output),
    ]


def _write_concat_list(images: list[Path], duration: float, path: Path) -> None:
    lines = []
    for img in images:
        lines.append(f"file '{img.resolve()}'\nduration {duration:.6f}")
    # concat demuxer は末尾フレームを自動的に切り捨てるため最後の1枚を重複させる
    if images:
        lines.append(f"file '{images[-1].resolve()}'")
    path.write_text("\n".join(lines))


def encode(
    images: list[Path],
    output: Path,
    duration_per_image: float = 0.3,
    fps: float = REELS_FPS,
    dry_run: bool = False,
) -> Path:
    if not images:
        raise ValueError("images が空です。")
    if dry_run:
        return output

    ffmpeg_path = check_ffmpeg()
    output.parent.mkdir(parents=True, exist_ok=True)

    # delete=False + 手動 unlink: Windows では NamedTemporaryFile を開いたまま
    # 別プロセス (ffmpeg) が読めないため、明示的にクローズしてから渡す必要がある
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        concat_path = Path(f.name)

    try:
        _write_concat_list(images, duration_per_image, concat_path)
        args = build_ffmpeg_args(
            images=images,
            output=output,
            fps=fps,
            duration_per_image=duration_per_image,
            ffmpeg_path=ffmpeg_path,
            concat_list_path=concat_path,
        )
        result = subprocess.run(args, capture_output=True, text=True)
        if result.returncode != 0:
            raise EncodingError(
                f"FFmpeg がエラーで終了しました (code={result.returncode}):\n{result.stderr[-2000:]}"
            )
    finally:
        concat_path.unlink(missing_ok=True)

    return output
