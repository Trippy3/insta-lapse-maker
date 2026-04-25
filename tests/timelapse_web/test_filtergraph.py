"""filtergraph.py のコマンド生成テスト。"""

from __future__ import annotations

from pathlib import Path

import pytest

from timelapse_web.models import Clip, CropRect, KenBurns, Project, Rect01
from timelapse_web.models.project import TextAnchor, TextOverlay, Transition, TransitionKind
from timelapse_web.services.filtergraph import (
    RenderPlan,
    RenderTarget,
    build_drawtext_filter,
    build_ffmpeg_command,
    build_filter_complex,
    build_zoompan_filter,
    escape_drawtext,
    find_font,
    plan_render,
)


def _project_2clips(tmp_path: Path) -> Project:
    p = tmp_path / "a.jpg"
    p.write_bytes(b"\x00")
    q = tmp_path / "b.jpg"
    q.write_bytes(b"\x00")
    return Project(
        clips=[
            Clip(id="c0", source_path=str(p), order_index=0, duration_s=1.0),
            Clip(id="c1", source_path=str(q), order_index=1, duration_s=1.5),
        ],
    )


def test_filter_complex_contains_scale_pad_and_concat(tmp_path: Path):
    project = _project_2clips(tmp_path)
    target = RenderTarget.from_project(project)
    fc = build_filter_complex(project, target)
    # 各入力をラベル付きで scale+pad
    assert "scale=1080:1920:force_original_aspect_ratio=decrease" in fc
    assert "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black" in fc
    # concat でまとめる
    assert "concat=n=2:v=1:a=0[vout]" in fc


def test_filter_complex_includes_crop_filter_when_set(tmp_path: Path):
    project = _project_2clips(tmp_path)
    project.clips[0].crop = CropRect(aspect="1:1", x=0.1, y=0.2, w=0.5, h=0.5)
    target = RenderTarget.from_project(project)
    fc = build_filter_complex(project, target)
    assert "crop=" in fc
    # 正規化座標が式に乗る
    assert "in_w*0.100000" in fc


def test_ffmpeg_command_has_required_flags(tmp_path: Path):
    project = _project_2clips(tmp_path)
    target = RenderTarget.from_project(project)
    out = tmp_path / "out.mp4"
    cmd = build_ffmpeg_command(project, target, out, ffmpeg_path="ffmpeg")
    # 必要なオプションが揃っていること
    joined = " ".join(cmd)
    assert "-c:v libx264" in joined
    assert "-movflags +faststart" in joined
    assert "-pix_fmt yuv420p" in joined
    assert "-filter_complex" in cmd
    # 各クリップに対して -loop 1 ... -i ... が並ぶ
    assert cmd.count("-loop") == 2
    # 無音ダミーの anullsrc 入力
    assert any("anullsrc" in c for c in cmd)


def test_proxy_target_is_even_resolution_half_default():
    p = Project()
    target = RenderTarget.proxy(p)
    assert target.width % 2 == 0
    assert target.height % 2 == 0
    assert target.width == 540
    assert target.height == 960
    assert target.fps == 15


def test_filter_complex_without_crop_has_no_crop_expr(tmp_path: Path):
    project = _project_2clips(tmp_path)
    target = RenderTarget.from_project(project)
    fc = build_filter_complex(project, target)
    assert "crop=" not in fc


def test_crop_filter_emits_all_four_normalized_values(tmp_path: Path):
    project = _project_2clips(tmp_path)
    project.clips[0].crop = CropRect(aspect="9:16", x=0.0, y=0.1, w=0.5625, h=1.0 - 0.1 - 1e-6)
    target = RenderTarget.from_project(project)
    fc = build_filter_complex(project, target)
    # 9:16 切り抜き後 → scale+pad で 1080x1920 にフィット
    assert "crop=" in fc
    assert "in_w*0.562500" in fc
    assert "in_h*0.100000" in fc


def test_crop_rect_pydantic_rejects_overflow():
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        CropRect(aspect="1:1", x=0.5, y=0.5, w=0.6, h=0.1)
    with pytest.raises(pydantic.ValidationError):
        CropRect(aspect="1:1", x=0.0, y=0.0, w=0.0, h=0.5)


def test_empty_project_raises(tmp_path: Path):
    project = Project()
    target = RenderTarget.from_project(project)
    with pytest.raises(ValueError):
        build_filter_complex(project, target)
    with pytest.raises(ValueError):
        build_ffmpeg_command(project, target, tmp_path / "x.mp4")


# ---- Ken Burns / zoompan ----

# 正規化座標での「正方形」が、9:16 キャンバス上では 9:16 ピクセルのビューポートになる
FULL_FRAME = Rect01(x=0.0, y=0.0, w=1.0, h=1.0)
CENTER_SMALL = Rect01(x=0.2, y=0.2, w=0.6, h=0.6)


def test_kenburns_rejects_non_square_normalized_rect():
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        KenBurns(
            start_rect=FULL_FRAME,
            # 横長 (w/h != 1) → 9:16 と合わない
            end_rect=Rect01(x=0.1, y=0.1, w=0.6, h=0.3),
        )


def test_zoompan_omitted_when_no_kenburns(tmp_path: Path):
    project = _project_2clips(tmp_path)
    target = RenderTarget.from_project(project)
    fc = build_filter_complex(project, target)
    assert "zoompan" not in fc


def test_zoompan_inserted_when_kenburns_set(tmp_path: Path):
    project = _project_2clips(tmp_path)
    project.clips[0].ken_burns = KenBurns(start_rect=FULL_FRAME, end_rect=CENTER_SMALL)
    target = RenderTarget.from_project(project)
    fc = build_filter_complex(project, target)
    assert "zoompan=" in fc
    assert f"s={target.width}x{target.height}" in fc


def test_zoompan_linear_expression_shape():
    kb = KenBurns(start_rect=FULL_FRAME, end_rect=CENTER_SMALL)
    target = RenderTarget(width=1080, height=1920, fps=30)
    expr = build_zoompan_filter(kb, duration_s=2.0, target=target)
    # d = 60 frames for 2s at 30fps
    assert "d=60" in expr
    # linear: on/59 が入る (d-1)
    assert "on/59" in expr
    # zoom は 1/w_interp 形式
    assert "z='(1/" in expr


def test_zoompan_ease_in_out_uses_cosine():
    kb = KenBurns(
        start_rect=FULL_FRAME,
        end_rect=CENTER_SMALL,
        easing=__import__("timelapse_web.models.project", fromlist=["KenBurnsEasing"]).KenBurnsEasing.EASE_IN_OUT,
    )
    target = RenderTarget(width=1080, height=1920, fps=30)
    expr = build_zoompan_filter(kb, duration_s=1.0, target=target)
    assert "cos(PI*" in expr


def test_zoompan_identical_rects_are_constant():
    kb = KenBurns(start_rect=CENTER_SMALL, end_rect=CENTER_SMALL)
    target = RenderTarget(width=1080, height=1920, fps=30)
    expr = build_zoompan_filter(kb, duration_s=3.0, target=target)
    # start == end のとき線形補間項は消え、定数式になる
    assert "on/" not in expr  # 補間項を含まない


def test_zoompan_short_clip_single_frame():
    kb = KenBurns(start_rect=FULL_FRAME, end_rect=CENTER_SMALL)
    # 0.02s * 30fps ≈ 1 frame
    target = RenderTarget(width=1080, height=1920, fps=30)
    expr = build_zoompan_filter(kb, duration_s=0.02, target=target)
    # d == 1 なので on/(d-1) を避けた定数 0 を使う
    assert "d=1:" in expr


# ---- Phase 4: トランジション / xfade ----


def _project_3clips(tmp_path: Path) -> Project:
    """3 クリップのプロジェクトを返す (transitions は空)。"""
    files = []
    for name in ("a.jpg", "b.jpg", "c.jpg"):
        p = tmp_path / name
        p.write_bytes(b"\x00")
        files.append(p)
    return Project(
        clips=[
            Clip(id="c0", source_path=str(files[0]), order_index=0, duration_s=1.0),
            Clip(id="c1", source_path=str(files[1]), order_index=1, duration_s=1.5),
            Clip(id="c2", source_path=str(files[2]), order_index=2, duration_s=1.0),
        ],
    )


def test_all_cut_transitions_uses_concat(tmp_path: Path):
    """transitions が空 (= すべて cut) のとき従来 concat を使う。"""
    project = _project_3clips(tmp_path)
    target = RenderTarget(width=1080, height=1920, fps=30)
    fc = build_filter_complex(project, target)
    assert "concat=n=3:v=1:a=0[vout]" in fc
    assert "xfade" not in fc


def test_explicit_cut_transitions_uses_concat(tmp_path: Path):
    """TransitionKind.CUT を明示しても concat になる。"""
    project = _project_3clips(tmp_path)
    project.transitions = [
        Transition(after_clip_id="c0", kind=TransitionKind.CUT, duration_s=0.0),
        Transition(after_clip_id="c1", kind=TransitionKind.CUT, duration_s=0.0),
    ]
    target = RenderTarget(width=1080, height=1920, fps=30)
    fc = build_filter_complex(project, target)
    assert "concat=n=3:v=1:a=0[vout]" in fc
    assert "xfade" not in fc


def test_xfade_filter_emitted_for_crossfade(tmp_path: Path):
    """crossfade トランジションで xfade=transition=dissolve が出る。"""
    project = _project_3clips(tmp_path)
    project.transitions = [
        Transition(after_clip_id="c1", kind=TransitionKind.CROSSFADE, duration_s=0.5),
    ]
    target = RenderTarget(width=1080, height=1920, fps=30)
    fc = build_filter_complex(project, target)
    assert "xfade=transition=dissolve" in fc
    assert "[vout]" in fc


def test_xfade_all_five_kinds_emit_correct_names(tmp_path: Path):
    """5 種のトランジションが FFmpeg xfade 名に正しくマップされる。"""
    expected = {
        TransitionKind.FADE: "fade",
        TransitionKind.CROSSFADE: "dissolve",
        TransitionKind.WIPE_LEFT: "wipeleft",
        TransitionKind.WIPE_RIGHT: "wiperight",
        TransitionKind.SLIDE_UP: "slideup",
    }
    for kind, ffname in expected.items():
        files = [tmp_path / f"{kind.value}_x.jpg", tmp_path / f"{kind.value}_y.jpg"]
        for f in files:
            f.write_bytes(b"\x00")
        p = Project(
            clips=[
                Clip(id="x0", source_path=str(files[0]), order_index=0, duration_s=1.0),
                Clip(id="x1", source_path=str(files[1]), order_index=1, duration_s=1.0),
            ],
            transitions=[
                Transition(after_clip_id="x0", kind=kind, duration_s=0.5),
            ],
        )
        fc = build_filter_complex(p, RenderTarget(width=1080, height=1920, fps=30))
        assert f"xfade=transition={ffname}" in fc, f"{kind} → {ffname} が見つからない"


def test_xfade_offset_single_transition(tmp_path: Path):
    """2 クリップ + 1 xfade (1.0s → 0.5s xfade): offset = dur_0 - td_0 = 0.5s。"""
    files = [tmp_path / "p.jpg", tmp_path / "q.jpg"]
    for f in files:
        f.write_bytes(b"\x00")
    project = Project(
        clips=[
            Clip(id="p0", source_path=str(files[0]), order_index=0, duration_s=1.0),
            Clip(id="p1", source_path=str(files[1]), order_index=1, duration_s=1.0),
        ],
        transitions=[
            Transition(after_clip_id="p0", kind=TransitionKind.FADE, duration_s=0.5),
        ],
    )
    target = RenderTarget(width=1080, height=1920, fps=30)
    fc = build_filter_complex(project, target)
    # offset = 1.0 - 0.5 = 0.5, rounded to fps
    assert "offset=0.500000" in fc


def test_xfade_offset_accumulates_correctly(tmp_path: Path):
    """3 クリップ + 2 xfade: offset_1 = (1.0-0.5) + (1.5-0.3) = 1.7s。"""
    files = [tmp_path / f"{n}.jpg" for n in ("a", "b", "c")]
    for f in files:
        f.write_bytes(b"\x00")
    project = Project(
        clips=[
            Clip(id="a0", source_path=str(files[0]), order_index=0, duration_s=1.0),
            Clip(id="a1", source_path=str(files[1]), order_index=1, duration_s=1.5),
            Clip(id="a2", source_path=str(files[2]), order_index=2, duration_s=1.0),
        ],
        transitions=[
            Transition(after_clip_id="a0", kind=TransitionKind.FADE, duration_s=0.5),
            Transition(after_clip_id="a1", kind=TransitionKind.CROSSFADE, duration_s=0.3),
        ],
    )
    target = RenderTarget(width=1080, height=1920, fps=30)
    fc = build_filter_complex(project, target)
    # offset_0 = 1.0 - 0.5 = 0.5
    assert "offset=0.500000" in fc
    # offset_1 = 0.5 + (1.5 - 0.3) = 1.7
    assert "offset=1.700000" in fc


def test_xfade_output_label_is_vout(tmp_path: Path):
    """最後の xfade の出力ラベルは [vout]。"""
    files = [tmp_path / f"{n}.jpg" for n in ("a", "b")]
    for f in files:
        f.write_bytes(b"\x00")
    project = Project(
        clips=[
            Clip(id="b0", source_path=str(files[0]), order_index=0, duration_s=1.0),
            Clip(id="b1", source_path=str(files[1]), order_index=1, duration_s=1.0),
        ],
        transitions=[
            Transition(after_clip_id="b0", kind=TransitionKind.WIPE_LEFT, duration_s=0.5),
        ],
    )
    target = RenderTarget(width=1080, height=1920, fps=30)
    fc = build_filter_complex(project, target)
    assert "[vout]" in fc


def test_mixed_cut_and_xfade(tmp_path: Path):
    """cut → xfade の混在: cut 側は concat、xfade 側は xfade フィルタを使う。"""
    files = [tmp_path / f"{n}.jpg" for n in ("a", "b", "c")]
    for f in files:
        f.write_bytes(b"\x00")
    # c0 →(cut)→ c1 →(xfade)→ c2
    project = Project(
        clips=[
            Clip(id="m0", source_path=str(files[0]), order_index=0, duration_s=1.0),
            Clip(id="m1", source_path=str(files[1]), order_index=1, duration_s=1.0),
            Clip(id="m2", source_path=str(files[2]), order_index=2, duration_s=1.0),
        ],
        transitions=[
            Transition(after_clip_id="m0", kind=TransitionKind.CUT, duration_s=0.0),
            Transition(after_clip_id="m1", kind=TransitionKind.FADE, duration_s=0.5),
        ],
    )
    target = RenderTarget(width=1080, height=1920, fps=30)
    fc = build_filter_complex(project, target)
    # c0 と c1 が concat でひとまとめになる
    assert "concat=n=2" in fc
    # その後 c2 と xfade
    assert "xfade=transition=fade" in fc


# ---- plan_render ----


def test_plan_render_single_stage_few_clips(tmp_path: Path):
    project = _project_2clips(tmp_path)
    target = RenderTarget.from_project(project)
    plan = plan_render(project, target)
    assert isinstance(plan, RenderPlan)
    assert not plan.two_stage


def test_plan_render_two_stage_many_clips(tmp_path: Path):
    files = []
    for i in range(26):
        p = tmp_path / f"img{i:02d}.jpg"
        p.write_bytes(b"\x00")
        files.append(p)
    project = Project(
        clips=[
            Clip(id=f"c{i}", source_path=str(files[i]), order_index=i, duration_s=0.5)
            for i in range(26)
        ]
    )
    target = RenderTarget.from_project(project)
    plan = plan_render(project, target)
    assert plan.two_stage


# ---- Phase 5: テキストオーバーレイ / drawtext ----


def _simple_overlay(**kw) -> TextOverlay:
    defaults = dict(text="Hello", start_s=0.0, end_s=2.0)
    defaults.update(kw)
    return TextOverlay(**defaults)


def _dummy_font(tmp_path: Path) -> Path:
    p = tmp_path / "dummy.ttf"
    p.write_bytes(b"")
    return p


# --- escape_drawtext ---

def test_escape_drawtext_single_quote():
    assert escape_drawtext("it's") == "it\\'s"


def test_escape_drawtext_colon():
    assert escape_drawtext("a:b") == "a\\:b"


def test_escape_drawtext_backslash():
    assert escape_drawtext("a\\b") == "a\\\\b"


def test_escape_drawtext_percent_brace():
    assert escape_drawtext("x%{pts}") == "x%%{pts}"


def test_escape_drawtext_newline_removed():
    result = escape_drawtext("line1\nline2")
    assert "\n" not in result


def test_escape_drawtext_injection():
    evil = "'; rm -rf /"
    result = escape_drawtext(evil)
    # no raw unescaped single quote (every ' should be preceded by \)
    assert "'" not in result.replace("\\'", "X")


def test_escape_drawtext_empty():
    assert escape_drawtext("") == ""


# --- find_font ---

def test_find_font_returns_existing_path():
    path = find_font()
    assert path.exists()
    assert path.suffix in (".ttf", ".otf", ".ttc")


# --- build_drawtext_filter ---

def test_build_drawtext_filter_contains_fontfile(tmp_path: Path):
    font = _dummy_font(tmp_path)
    ov = _simple_overlay(text="Hello", font_size_px=64, color_hex="#FFFFFF",
                         x=0.5, y=0.5, anchor=TextAnchor.CENTER, start_s=0.0, end_s=2.0)
    f = build_drawtext_filter(ov, font)
    assert "fontfile=" in f
    assert str(font) in f


def test_build_drawtext_filter_text_escaped(tmp_path: Path):
    font = _dummy_font(tmp_path)
    ov = _simple_overlay(text="it's here", start_s=0.0, end_s=1.0)
    f = build_drawtext_filter(ov, font)
    assert "text='it\\'s here'" in f


def test_build_drawtext_filter_fontsize(tmp_path: Path):
    font = _dummy_font(tmp_path)
    ov = _simple_overlay(font_size_px=128, start_s=0.0, end_s=1.0)
    f = build_drawtext_filter(ov, font)
    assert "fontsize=128" in f


def test_build_drawtext_filter_color_hex_converted(tmp_path: Path):
    font = _dummy_font(tmp_path)
    ov = _simple_overlay(color_hex="#FF8800", start_s=0.0, end_s=1.0)
    f = build_drawtext_filter(ov, font)
    assert "fontcolor=0xFF8800" in f


def test_build_drawtext_filter_enable_expr(tmp_path: Path):
    font = _dummy_font(tmp_path)
    ov = _simple_overlay(start_s=1.5, end_s=4.0)
    f = build_drawtext_filter(ov, font)
    assert "enable='between(t,1.5,4.0)'" in f


def test_build_drawtext_filter_stroke_present(tmp_path: Path):
    font = _dummy_font(tmp_path)
    ov = _simple_overlay(stroke_color_hex="#000000", stroke_width_px=3, start_s=0.0, end_s=1.0)
    f = build_drawtext_filter(ov, font)
    assert "borderw=3" in f
    assert "bordercolor=0x000000" in f


def test_build_drawtext_filter_no_stroke_when_none(tmp_path: Path):
    font = _dummy_font(tmp_path)
    ov = _simple_overlay(stroke_color_hex=None, stroke_width_px=0, start_s=0.0, end_s=1.0)
    f = build_drawtext_filter(ov, font)
    assert "borderw" not in f


def test_build_drawtext_filter_fade_alpha_included(tmp_path: Path):
    font = _dummy_font(tmp_path)
    ov = _simple_overlay(fade_in_s=0.5, fade_out_s=0.3, start_s=0.0, end_s=3.0)
    f = build_drawtext_filter(ov, font)
    assert "alpha=" in f


def test_build_drawtext_filter_no_fade_no_alpha(tmp_path: Path):
    font = _dummy_font(tmp_path)
    ov = _simple_overlay(fade_in_s=0.0, fade_out_s=0.0, start_s=0.0, end_s=2.0)
    f = build_drawtext_filter(ov, font)
    assert "alpha=" not in f


def test_build_drawtext_filter_center_anchor_uses_tw_th(tmp_path: Path):
    font = _dummy_font(tmp_path)
    ov = _simple_overlay(x=0.5, y=0.5, anchor=TextAnchor.CENTER, start_s=0.0, end_s=1.0)
    f = build_drawtext_filter(ov, font)
    assert "tw/2" in f
    assert "th/2" in f


def test_build_drawtext_filter_top_left_anchor_no_offset(tmp_path: Path):
    font = _dummy_font(tmp_path)
    # stroke を無効化して borderw が混入しないようにする
    ov = _simple_overlay(
        x=0.1, y=0.1, anchor=TextAnchor.TOP_LEFT,
        stroke_color_hex=None, stroke_width_px=0,
        start_s=0.0, end_s=1.0,
    )
    f = build_drawtext_filter(ov, font)
    # top_left: x/y 式に tw/th の減算が含まれない (CENTER 用の -tw/2 が不在)
    assert "tw/2" not in f
    assert "th/2" not in f
    assert "x=W*0.1" in f
    assert "y=H*0.1" in f


# --- filter_complex with overlays ---

def test_filter_complex_with_single_overlay_includes_drawtext(tmp_path: Path):
    project = _project_2clips(tmp_path)
    project = project.model_copy(update={
        "overlays": [TextOverlay(text="Test", start_s=0.0, end_s=1.0)]
    })
    target = RenderTarget(width=1080, height=1920, fps=30)
    fc = build_filter_complex(project, target)
    assert "drawtext=" in fc
    assert fc.endswith("[vout]")


def test_filter_complex_with_overlays_chains_correctly(tmp_path: Path):
    project = _project_2clips(tmp_path)
    project = project.model_copy(update={
        "overlays": [
            TextOverlay(text="first", start_s=0.0, end_s=1.0),
            TextOverlay(text="second", start_s=0.5, end_s=2.0),
        ]
    })
    target = RenderTarget(width=1080, height=1920, fps=30)
    fc = build_filter_complex(project, target)
    assert fc.count("drawtext=") == 2
    assert "[vout]" in fc


def test_filter_complex_no_overlays_unchanged(tmp_path: Path):
    project = _project_2clips(tmp_path)
    target = RenderTarget(width=1080, height=1920, fps=30)
    fc = build_filter_complex(project, target)
    assert "drawtext" not in fc
    assert "concat=n=2:v=1:a=0[vout]" in fc
