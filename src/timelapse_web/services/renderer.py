"""レンダ実行: filter_complex を FFmpeg に流し、進捗をコールバック配信。"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from timelapse.reels_spec import AUDIO_BITRATE, AUDIO_CHANNELS, AUDIO_CODEC, AUDIO_SAMPLE_RATE, MOVFLAGS, VIDEO_BITRATE, VIDEO_BUFSIZE, VIDEO_CODEC, VIDEO_GOP_SEC, VIDEO_LEVEL, VIDEO_MAX_B_FRAMES, VIDEO_MAXRATE, VIDEO_PIX_FMT, VIDEO_PROFILE
from timelapse.system import check_ffmpeg

from ..models import Clip, Project
from ..models.project import TextOverlay, Transition, TransitionKind
from .filtergraph import (
    RenderTarget,
    _XFADE_NAMES,
    build_clip_chain,
    build_drawtext_filter,
    build_ffmpeg_command,
    find_font,
    plan_render,
)

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[float], None]


def _total_duration_us(project: Project) -> int:
    return int(project.total_visible_duration_s() * 1_000_000)


def _run_ffmpeg(cmd: list[str], total_us: int, on_progress: ProgressCallback | None) -> None:
    """FFmpeg を起動して進捗を配信する。失敗時は RuntimeError を送出。"""
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            if line.startswith("out_time_us=") or line.startswith("out_time_ms="):
                try:
                    value = int(line.split("=", 1)[1])
                except ValueError:
                    continue
                if on_progress is not None:
                    ratio = max(0.0, min(1.0, value / max(1, total_us)))
                    on_progress(ratio)
            elif line == "progress=end":
                if on_progress is not None:
                    on_progress(1.0)
    finally:
        proc.wait()
    if proc.returncode != 0:
        stderr_tail = (proc.stderr.read() if proc.stderr else "")[-2000:]
        raise RuntimeError(
            f"FFmpeg が失敗しました (code={proc.returncode}):\n{stderr_tail}"
        )


def _build_clip_only_command(
    clip: Clip,
    target: RenderTarget,
    output: Path,
    clip_index: int,
    ffmpeg_path: str,
) -> list[str]:
    """1 クリップを単独 MP4 に書き出すコマンド。"""
    from pathlib import Path as _Path
    cmd = [ffmpeg_path, "-y", "-hide_banner", "-loglevel", "error", "-progress", "pipe:1"]
    cmd += [
        "-loop", "1",
        "-framerate", str(target.fps),
        "-t", f"{clip.duration_s:.6f}",
        "-i", str(_Path(clip.source_path).expanduser().resolve()),
    ]
    anull_idx = 1
    cmd += ["-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate={AUDIO_SAMPLE_RATE}"]

    chain = build_clip_chain(clip, target, 0)
    cmd += ["-filter_complex", chain]

    gop = int(target.fps * VIDEO_GOP_SEC)
    cmd += [
        "-map", "[v0]",
        "-map", f"{anull_idx}:a",
        "-c:v", VIDEO_CODEC,
        "-profile:v", VIDEO_PROFILE,
        "-level:v", VIDEO_LEVEL,
        "-b:v", target.video_bitrate,
        "-maxrate", target.video_maxrate,
        "-bufsize", target.video_bufsize,
        "-g", str(gop),
        "-bf", str(VIDEO_MAX_B_FRAMES),
        "-pix_fmt", VIDEO_PIX_FMT,
        "-r", str(target.fps),
        "-c:a", AUDIO_CODEC,
        "-b:a", AUDIO_BITRATE,
        "-ac", str(AUDIO_CHANNELS),
        "-ar", str(AUDIO_SAMPLE_RATE),
        "-shortest",
        "-movflags", MOVFLAGS,
        str(output),
    ]
    return cmd


def _build_concat_xfade_command(
    clip_paths: list[Path],
    clip_durations: list[float],
    transitions: list[Transition | None],
    target: RenderTarget,
    output: Path,
    ffmpeg_path: str,
    overlays: list[TextOverlay] | None = None,
) -> list[str]:
    """Stage 2: 個別 MP4 を xfade/concat で連結するコマンド。"""
    n = len(clip_paths)
    cmd = [ffmpeg_path, "-y", "-hide_banner", "-loglevel", "error", "-progress", "pipe:1"]
    for p in clip_paths:
        cmd += ["-i", str(p)]
    anull_idx = n
    cmd += ["-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate={AUDIO_SAMPLE_RATE}"]

    filters: list[str] = []
    has_overlays = bool(overlays)
    base_label = "vout_base" if has_overlays else "vout"

    # Check if any non-cut transition
    has_xfade = any(tr is not None and tr.kind != TransitionKind.CUT for tr in transitions)

    if not has_xfade:
        inputs = "".join(f"[{i}:v]" for i in range(n))
        filters.append(f"{inputs}concat=n={n}:v=1:a=0[{base_label}]")
    else:
        # Group into segments (same logic as filtergraph)
        segments: list[tuple[list[tuple[int, float]], Transition | None]] = []
        current: list[tuple[int, float]] = [(0, clip_durations[0])]
        for i in range(1, n):
            tr = transitions[i - 1]
            if tr is None or tr.kind == TransitionKind.CUT:
                current.append((i, clip_durations[i]))
            else:
                segments.append((current, tr))
                current = [(i, clip_durations[i])]
        segments.append((current, None))

        seg_labels: list[str] = []
        for k, (seg_items, _) in enumerate(segments):
            if len(seg_items) == 1:
                idx = seg_items[0][0]
                seg_labels.append(f"{idx}:v")
            else:
                inputs = "".join(f"[{idx}:v]" for idx, _ in seg_items)
                label = f"seg{k}"
                filters.append(f"{inputs}concat=n={len(seg_items)}:v=1:a=0[{label}]")
                seg_labels.append(label)

        seg_durations = [sum(dur for _, dur in items) for items, _ in segments]
        seg_transitions = [tr for _, tr in segments[:-1]]

        prev_label = seg_labels[0]
        for k, tr in enumerate(seg_transitions):
            assert tr is not None
            xfade_name = _XFADE_NAMES[tr.kind]
            xfade_dur = tr.duration_s
            offset = sum(
                seg_durations[i] - seg_transitions[i].duration_s
                for i in range(k + 1)
            )
            offset = round(offset * target.fps) / target.fps
            out_label = base_label if k == len(seg_transitions) - 1 else f"xf{k}"
            filters.append(
                f"[{prev_label}][{seg_labels[k + 1]}]"
                f"xfade=transition={xfade_name}:duration={xfade_dur}:offset={offset:.6f}"
                f"[{out_label}]"
            )
            prev_label = out_label

    # Stage 2 の drawtext チェーン (オーバーレイがある場合)
    if has_overlays:
        assert overlays is not None
        font_path = find_font()
        prev = base_label
        for i, overlay in enumerate(overlays):
            out = "vout" if i == len(overlays) - 1 else f"vd{i}"
            dt = build_drawtext_filter(overlay, font_path)
            filters.append(f"[{prev}]{dt}[{out}]")
            prev = out

    gop = int(target.fps * VIDEO_GOP_SEC)
    cmd += ["-filter_complex", ";".join(filters)]
    cmd += [
        "-map", "[vout]",
        "-map", f"{anull_idx}:a",
        "-c:v", VIDEO_CODEC,
        "-profile:v", VIDEO_PROFILE,
        "-level:v", VIDEO_LEVEL,
        "-b:v", target.video_bitrate,
        "-maxrate", target.video_maxrate,
        "-bufsize", target.video_bufsize,
        "-g", str(gop),
        "-bf", str(VIDEO_MAX_B_FRAMES),
        "-pix_fmt", VIDEO_PIX_FMT,
        "-r", str(target.fps),
        "-c:a", AUDIO_CODEC,
        "-b:a", AUDIO_BITRATE,
        "-ac", str(AUDIO_CHANNELS),
        "-ar", str(AUDIO_SAMPLE_RATE),
        "-shortest",
        "-movflags", MOVFLAGS,
        str(output),
    ]
    return cmd


def run_two_stage_render(
    project: Project,
    target: RenderTarget,
    output: Path,
    on_progress: ProgressCallback | None = None,
    ffmpeg_path: str | None = None,
) -> Path:
    """二段階レンダ: クリップ → 個別 MP4、次に xfade 連結。"""
    if ffmpeg_path is None:
        ffmpeg_path = check_ffmpeg()
    clips = project.sorted_clips()
    tr_by_clip_id = {t.after_clip_id: t for t in project.transitions}
    output.parent.mkdir(parents=True, exist_ok=True)
    total_clips = len(clips)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        clip_paths: list[Path] = []

        # Stage 1: 各クリップを個別 MP4 化 (進捗 0..0.8)
        for idx, clip in enumerate(clips):
            clip_out = tmp_dir / f"clip_{idx:04d}.mp4"
            cmd = _build_clip_only_command(clip, target, clip_out, idx, ffmpeg_path)
            clip_total_us = int(clip.duration_s * 1_000_000)

            def _stage1_progress(ratio: float, i: int = idx) -> None:
                if on_progress is not None:
                    overall = ((i + ratio) / total_clips) * 0.8
                    on_progress(overall)

            logger.debug("stage1 clip %d: %s", idx, " ".join(cmd))
            _run_ffmpeg(cmd, clip_total_us, _stage1_progress)
            clip_paths.append(clip_out)

        # Stage 2: xfade 連結 + drawtext オーバーレイ (進捗 0.8..1.0)
        transitions = [tr_by_clip_id.get(c.id) for c in clips[:-1]]
        clip_durations = [c.duration_s for c in clips]
        stage2_cmd = _build_concat_xfade_command(
            clip_paths, clip_durations, transitions, target, output, ffmpeg_path,
            overlays=project.overlays if project.overlays else None,
        )

        total_us = _total_duration_us(project)

        def _stage2_progress(ratio: float) -> None:
            if on_progress is not None:
                on_progress(0.8 + ratio * 0.2)

        logger.debug("stage2: %s", " ".join(stage2_cmd))
        _run_ffmpeg(stage2_cmd, total_us, _stage2_progress)

    if on_progress is not None:
        on_progress(1.0)
    return output


def run_render(
    project: Project,
    target: RenderTarget,
    output: Path,
    on_progress: ProgressCallback | None = None,
) -> Path:
    """レンダを実行する。クリップ数が多い場合は自動的に二段階レンダに切り替える。"""
    plan = plan_render(project, target)
    if plan.two_stage:
        logger.info("二段階レンダを使用: %s", plan.reason)
        return run_two_stage_render(project, target, output, on_progress)

    ffmpeg_path = check_ffmpeg()
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_ffmpeg_command(project, target, output, ffmpeg_path=ffmpeg_path)
    total_us = max(1, _total_duration_us(project))
    logger.debug("ffmpeg cmd: %s", " ".join(cmd))
    _run_ffmpeg(cmd, total_us, on_progress)
    return output
