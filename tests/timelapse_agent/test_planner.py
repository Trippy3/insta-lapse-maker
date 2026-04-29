"""planner.py のユニットテスト。"""

from __future__ import annotations

from pathlib import Path

import pytest

from timelapse_agent.planner import scaffold_project
from timelapse_web.models.project import TransitionKind


def _fake_paths(n: int, tmp_path: Path) -> list[Path]:
    paths = []
    for i in range(n):
        p = tmp_path / f"img_{i:03d}.jpg"
        p.write_bytes(b"\xff\xd8\xff")  # 最小 JPEG ヘッダ
        paths.append(p)
    return paths


def test_scaffold_project_creates_correct_clips(tmp_path: Path) -> None:
    paths = _fake_paths(5, tmp_path)
    project = scaffold_project(paths, default_duration_s=1.0)

    assert len(project.clips) == 5
    for i, clip in enumerate(project.sorted_clips()):
        assert clip.order_index == i
        assert clip.duration_s == pytest.approx(1.0)
        assert clip.crop is None
        assert clip.ken_burns is None


def test_scaffold_project_no_transitions_for_cut(tmp_path: Path) -> None:
    paths = _fake_paths(3, tmp_path)
    project = scaffold_project(
        paths,
        default_transition=TransitionKind.CUT,
        transition_duration_s=0.5,
    )
    assert project.transitions == []


def test_scaffold_project_creates_transitions_for_crossfade(tmp_path: Path) -> None:
    paths = _fake_paths(4, tmp_path)
    project = scaffold_project(
        paths,
        default_duration_s=1.0,
        default_transition=TransitionKind.CROSSFADE,
        transition_duration_s=0.3,
    )
    assert len(project.transitions) == 3
    sorted_clips = project.sorted_clips()
    for i, tr in enumerate(project.transitions):
        assert tr.kind == TransitionKind.CROSSFADE
        assert tr.duration_s == pytest.approx(0.3)
        assert tr.after_clip_id == sorted_clips[i].id


def test_scaffold_project_total_duration(tmp_path: Path) -> None:
    paths = _fake_paths(5, tmp_path)
    project = scaffold_project(
        paths,
        default_duration_s=1.0,
        default_transition=TransitionKind.CROSSFADE,
        transition_duration_s=0.5,
    )
    # 5 clips * 1.0s - 4 transitions * 0.5s = 3.0s
    assert project.total_visible_duration_s() == pytest.approx(3.0)


def test_scaffold_project_source_paths_are_absolute(tmp_path: Path) -> None:
    paths = _fake_paths(2, tmp_path)
    project = scaffold_project(paths)
    for clip in project.clips:
        assert Path(clip.source_path).is_absolute()


def test_scaffold_project_name(tmp_path: Path) -> None:
    paths = _fake_paths(1, tmp_path)
    project = scaffold_project(paths, name="My Painting")
    assert project.name == "My Painting"


def test_scaffold_project_zero_transition_duration_produces_no_transitions(tmp_path: Path) -> None:
    paths = _fake_paths(3, tmp_path)
    project = scaffold_project(
        paths,
        default_transition=TransitionKind.FADE,
        transition_duration_s=0.0,
    )
    assert project.transitions == []
