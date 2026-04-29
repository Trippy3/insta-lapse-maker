"""timelapse_agent CLI のスモークテスト。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image


def _make_jpeg(path: Path, width: int = 200, height: int = 200) -> None:
    Image.new("RGB", (width, height), color=(100, 150, 200)).save(path, "JPEG")


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "timelapse_agent", *args],
        capture_output=True,
        text=True,
    )


def test_inspect_outputs_valid_json(tmp_path: Path) -> None:
    _make_jpeg(tmp_path / "a.jpg", 300, 400)
    _make_jpeg(tmp_path / "b.jpg", 400, 300)

    result = _run("inspect", str(tmp_path))

    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["filename"] in ("a.jpg", "b.jpg")
    assert "width" in data[0]
    assert "aspect_ratio" in data[0]


def test_inspect_returns_error_on_empty_dir(tmp_path: Path) -> None:
    result = _run("inspect", str(tmp_path))
    assert result.returncode != 0


def test_scaffold_creates_project_file(tmp_path: Path) -> None:
    for name in ("img_1.jpg", "img_2.jpg", "img_3.jpg"):
        _make_jpeg(tmp_path / name)
    out = tmp_path / "project.tlproj.json"

    result = _run(
        "scaffold", str(tmp_path),
        "--output", str(out),
        "--duration", "0.8",
        "--transition", "crossfade",
        "--transition-duration", "0.3",
        "--name", "Test Project",
    )

    assert result.returncode == 0, result.stderr
    response = json.loads(result.stdout)
    assert response["status"] == "ok"
    assert response["clip_count"] == 3
    assert out.is_file()


def test_scaffold_project_json_is_valid_project(tmp_path: Path) -> None:
    for name in ("a.jpg", "b.jpg"):
        _make_jpeg(tmp_path / name)
    out = tmp_path / "p.tlproj.json"

    _run("scaffold", str(tmp_path), "--output", str(out))

    from timelapse_web.services.project_store import load_project
    project = load_project(out)
    assert len(project.clips) == 2
    assert project.sorted_clips()[0].order_index == 0


def test_scaffold_unknown_transition_exits_nonzero(tmp_path: Path) -> None:
    _make_jpeg(tmp_path / "a.jpg")
    out = tmp_path / "p.tlproj.json"
    result = _run(
        "scaffold", str(tmp_path),
        "--output", str(out),
        "--transition", "rainbow",
    )
    assert result.returncode != 0


def test_render_dry_run_outputs_plan(tmp_path: Path) -> None:
    for name in ("a.jpg", "b.jpg"):
        _make_jpeg(tmp_path / name)
    proj = tmp_path / "p.tlproj.json"
    _run("scaffold", str(tmp_path), "--output", str(proj), "--duration", "1.0")

    result = _run("render", str(proj), "--dry-run")

    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    assert plan["status"] == "ok"
    assert "two_stage" in plan
    assert "duration_s" in plan
    assert plan["clip_count"] == 2


@pytest.mark.integration
def test_render_produces_mp4(tmp_path: Path) -> None:
    for name in ("a.jpg", "b.jpg"):
        _make_jpeg(tmp_path / name)
    proj = tmp_path / "p.tlproj.json"
    _run("scaffold", str(tmp_path), "--output", str(proj), "--duration", "0.5")
    out_mp4 = tmp_path / "out.mp4"

    result = _run("render", str(proj), "--output", str(out_mp4))

    assert result.returncode == 0, result.stderr
    response = json.loads(result.stdout)
    assert response["status"] == "ok"
    assert out_mp4.is_file()
    assert out_mp4.stat().st_size > 0
