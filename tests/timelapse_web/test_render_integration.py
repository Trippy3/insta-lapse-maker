"""実際に FFmpeg を起動して MP4 が生成されるかの統合テスト。"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from timelapse_web.models import Clip, KenBurns, Project, Rect01
from timelapse_web.models.project import TextOverlay, Transition, TransitionKind
from timelapse_web.services.filtergraph import RenderTarget
from timelapse_web.services.renderer import run_render, run_two_stage_render


pytestmark = pytest.mark.integration


@pytest.fixture()
def ffmpeg_present():
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg 未インストール")


def _make_image(path: Path, color: tuple[int, int, int], size=(800, 600)) -> Path:
    Image.new("RGB", size, color).save(path, format="JPEG", quality=85)
    return path


def test_render_produces_playable_mp4(tmp_path: Path, ffmpeg_present):
    a = _make_image(tmp_path / "a.jpg", (200, 30, 30))
    b = _make_image(tmp_path / "b.jpg", (30, 200, 30))
    project = Project(
        clips=[
            Clip(id="c0", source_path=str(a), order_index=0, duration_s=0.4),
            Clip(id="c1", source_path=str(b), order_index=1, duration_s=0.4),
        ],
    )
    target = RenderTarget.proxy(project)  # 高速化のため 540x960/15fps
    out = tmp_path / "out.mp4"

    progress_values: list[float] = []
    run_render(project, target, out, on_progress=progress_values.append)

    assert out.is_file()
    assert out.stat().st_size > 0
    # ffprobe で解像度とコーデックを確認
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height",
            "-of", "csv=p=0",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    parts = probe.stdout.strip().split(",")
    assert parts[0] == "h264"
    assert parts[1] == str(target.width)
    assert parts[2] == str(target.height)
    # 進捗が単調増加で最終的に 1.0 に到達
    assert progress_values, "進捗コールバックが呼ばれていない"
    assert progress_values[-1] == pytest.approx(1.0)


def test_render_with_ken_burns_produces_mp4(tmp_path: Path, ffmpeg_present):
    """Ken Burns (zoompan) ありのクリップで最後まで完走することを保証する。

    矩形は正規化 0..1 で w == h (9:16 キャンバス上の 9:16 ビューポート)。
    """
    a = _make_image(tmp_path / "a.jpg", (40, 80, 200), size=(1200, 1200))
    project = Project(
        clips=[
            Clip(
                id="c0",
                source_path=str(a),
                order_index=0,
                duration_s=0.5,
                ken_burns=KenBurns(
                    start_rect=Rect01(x=0.0, y=0.0, w=1.0, h=1.0),
                    end_rect=Rect01(x=0.2, y=0.2, w=0.5, h=0.5),
                ),
            ),
        ],
    )
    target = RenderTarget.proxy(project)
    out = tmp_path / "kb.mp4"
    run_render(project, target, out)
    assert out.is_file()
    assert out.stat().st_size > 0
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height",
            "-of", "csv=p=0",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    parts = probe.stdout.strip().split(",")
    assert parts[0] == "h264"
    assert parts[1] == str(target.width)
    assert parts[2] == str(target.height)


def _probe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def test_render_with_crossfade_transition(tmp_path: Path, ffmpeg_present):
    """crossfade トランジションで MP4 が生成され、尺が total_visible_duration_s と一致する。"""
    a = _make_image(tmp_path / "a.jpg", (200, 50, 50))
    b = _make_image(tmp_path / "b.jpg", (50, 200, 50))
    project = Project(
        clips=[
            Clip(id="c0", source_path=str(a), order_index=0, duration_s=1.0),
            Clip(id="c1", source_path=str(b), order_index=1, duration_s=1.0),
        ],
        transitions=[
            Transition(after_clip_id="c0", kind=TransitionKind.CROSSFADE, duration_s=0.5),
        ],
    )
    target = RenderTarget.proxy(project)
    out = tmp_path / "xfade.mp4"
    run_render(project, target, out)
    assert out.is_file() and out.stat().st_size > 0
    dur = _probe_duration(out)
    expected = project.total_visible_duration_s()
    # xfade のフレーム境界丸めにより最大 1 フレーム分 (proxy 15fps で ~0.067s) の誤差を許容
    assert abs(dur - expected) < 0.15, f"尺 {dur:.3f}s が期待値 {expected:.3f}s と乖離"


def test_two_stage_render_matches_single_stage(tmp_path: Path, ffmpeg_present):
    """二段階レンダの出力尺が単一グラフ版と一致する。"""
    files = []
    for i in range(4):
        p = _make_image(tmp_path / f"img{i}.jpg", (i * 50, 100, 200 - i * 40))
        files.append(p)
    clips = [
        Clip(id=f"c{i}", source_path=str(files[i % 4]), order_index=i, duration_s=0.4)
        for i in range(4)
    ]
    project = Project(
        clips=clips,
        transitions=[
            Transition(after_clip_id="c1", kind=TransitionKind.FADE, duration_s=0.2),
        ],
    )
    target = RenderTarget.proxy(project)

    out_single = tmp_path / "single.mp4"
    run_render(project, target, out_single)

    out_two = tmp_path / "two_stage.mp4"
    run_two_stage_render(project, target, out_two)

    dur_single = _probe_duration(out_single)
    dur_two = _probe_duration(out_two)
    assert abs(dur_single - dur_two) < 0.15, (
        f"単一 {dur_single:.3f}s vs 二段階 {dur_two:.3f}s の差が大きい"
    )


def test_render_with_mixed_cut_and_xfade_transitions(tmp_path: Path, ffmpeg_present):
    """CUT + XFADE 混在で動画生成が成功すること (回帰テスト)。

    concat の出力タイムベース (1/1000000) と xfade の入力タイムベース (1/{fps})
    が不一致になり「First input link main timebase do not match the
    corresponding second input link xfade timebase」エラーで失敗していた。
    """
    files = [
        _make_image(tmp_path / f"mix{i}.jpg", (i * 30, 100, 200 - i * 30))
        for i in range(5)
    ]
    project = Project(
        clips=[
            Clip(id=f"m{i}", source_path=str(files[i]), order_index=i, duration_s=0.5)
            for i in range(5)
        ],
        # m0→(cut)→m1→(fade)→m2→(cut)→m3→(fade)→m4
        # → 単一クリップ + 複数クリップ concat の混在パターンを再現
        transitions=[
            Transition(after_clip_id="m0", kind=TransitionKind.CUT, duration_s=0.0),
            Transition(after_clip_id="m1", kind=TransitionKind.FADE, duration_s=0.2),
            Transition(after_clip_id="m2", kind=TransitionKind.CUT, duration_s=0.0),
            Transition(after_clip_id="m3", kind=TransitionKind.FADE, duration_s=0.2),
        ],
    )
    target = RenderTarget.proxy(project)

    # 単一ステージ
    out_single = tmp_path / "mixed_single.mp4"
    run_render(project, target, out_single)
    assert out_single.is_file() and out_single.stat().st_size > 0

    # 二段階ステージ (実運用では plan_render で xfade ありなら強制 two-stage)
    out_two = tmp_path / "mixed_two.mp4"
    run_two_stage_render(project, target, out_two)
    assert out_two.is_file() and out_two.stat().st_size > 0


def test_render_with_text_overlay_produces_mp4(tmp_path: Path, ffmpeg_present):
    """テキストオーバーレイがある状態で最終 MP4 が生成される。"""
    a = _make_image(tmp_path / "a.jpg", (30, 80, 200))
    project = Project(
        clips=[
            Clip(id="c0", source_path=str(a), order_index=0, duration_s=1.0),
        ],
        overlays=[
            TextOverlay(text="テスト", start_s=0.0, end_s=1.0, fade_in_s=0.2, fade_out_s=0.2),
        ],
    )
    target = RenderTarget.proxy(project)
    out = tmp_path / "overlay.mp4"
    run_render(project, target, out)
    assert out.is_file() and out.stat().st_size > 0
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name,width,height",
         "-of", "csv=p=0", str(out)],
        capture_output=True, text=True, check=True,
    )
    parts = probe.stdout.strip().split(",")
    assert parts[0] == "h264"
    assert parts[1] == str(target.width)


def test_two_stage_render_with_overlay_produces_mp4(tmp_path: Path, ffmpeg_present):
    """二段階レンダでもテキストオーバーレイが正常に出力される。"""
    files = []
    for i in range(4):
        p = _make_image(tmp_path / f"img{i}.jpg", (i * 50, 100, 200 - i * 40))
        files.append(p)
    project = Project(
        clips=[
            Clip(id=f"c{i}", source_path=str(files[i % 4]), order_index=i, duration_s=0.4)
            for i in range(4)
        ],
        overlays=[
            TextOverlay(text="Stage2 Overlay", start_s=0.0, end_s=1.0),
        ],
    )
    target = RenderTarget.proxy(project)
    out = tmp_path / "two_overlay.mp4"
    run_two_stage_render(project, target, out)
    assert out.is_file() and out.stat().st_size > 0
