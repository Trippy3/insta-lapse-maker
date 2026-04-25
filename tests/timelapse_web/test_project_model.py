"""Project / Clip / Transition モデルのバリデーションテスト。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from timelapse_web.models import (
    Clip,
    CropRect,
    Project,
    TextOverlay,
    Transition,
    TransitionKind,
)


def _clip(idx: int, duration: float = 0.5, path: str = "/tmp/dummy.jpg") -> Clip:
    return Clip(id=f"c{idx}", source_path=path, order_index=idx, duration_s=duration)


def test_project_total_duration_with_cut_transitions():
    clips = [_clip(0, 1.0), _clip(1, 2.0), _clip(2, 3.0)]
    p = Project(clips=clips)
    # cut しかないので素直に合計
    assert p.total_visible_duration_s() == pytest.approx(6.0)


def test_project_total_duration_subtracts_xfade_overlap():
    clips = [_clip(0, 2.0), _clip(1, 2.0), _clip(2, 2.0)]
    trs = [
        Transition(after_clip_id="c0", kind=TransitionKind.CROSSFADE, duration_s=0.5),
        Transition(after_clip_id="c1", kind=TransitionKind.FADE, duration_s=0.5),
    ]
    p = Project(clips=clips, transitions=trs)
    # 2 つの重なり (各 0.5s) を差し引く
    assert p.total_visible_duration_s() == pytest.approx(5.0)


def test_project_rejects_over_90s():
    # 100 秒になるクリップ列は総尺チェックで拒否される
    clips = [_clip(i, 10.0) for i in range(10)]
    with pytest.raises(ValidationError):
        Project(clips=clips)


def test_overlay_rejects_end_beyond_total():
    clips = [_clip(0, 1.0), _clip(1, 1.0)]
    overlay = TextOverlay(
        text="hello",
        start_s=0.0,
        end_s=5.0,  # 総尺 2s を超える
    )
    with pytest.raises(ValidationError):
        Project(clips=clips, overlays=[overlay])


def test_crop_rect_rejects_out_of_bounds():
    with pytest.raises(ValidationError):
        CropRect(aspect="1:1", x=0.6, y=0.0, w=0.5, h=0.5)


def test_text_overlay_normalizes_hex_color():
    o = TextOverlay(text="hi", color_hex="#ffcc00")
    assert o.color_hex == "#FFCC00"


def test_text_overlay_rejects_end_le_start():
    with pytest.raises(ValidationError):
        TextOverlay(text="hi", start_s=1.0, end_s=1.0)
