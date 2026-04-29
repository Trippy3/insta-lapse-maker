"""grid_overlay モジュールおよび crop-grid CLI のテスト。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from timelapse_agent.grid_overlay import (
    GridResult,
    overlay_grid,
    overlay_grid_directory,
)


def _make_jpeg(path: Path, width: int = 1200, height: int = 1600) -> None:
    Image.new("RGB", (width, height), color=(180, 180, 180)).save(path, "JPEG")


def test_overlay_grid_returns_result_within_max_side(tmp_path: Path) -> None:
    src = tmp_path / "src.jpg"
    _make_jpeg(src, 3000, 4000)
    dst = tmp_path / "out.jpg"

    result = overlay_grid(src, dst, max_side=900)

    assert isinstance(result, GridResult)
    assert max(result.width, result.height) == 900
    assert result.output == dst
    assert dst.exists()
    with Image.open(dst) as out_img:
        assert out_img.size == (result.width, result.height)


def test_overlay_grid_does_not_upscale_smaller_image(tmp_path: Path) -> None:
    src = tmp_path / "src.jpg"
    _make_jpeg(src, 400, 600)
    dst = tmp_path / "out.jpg"

    result = overlay_grid(src, dst, max_side=900)

    assert (result.width, result.height) == (400, 600)


def test_overlay_grid_creates_parent_dir(tmp_path: Path) -> None:
    src = tmp_path / "src.jpg"
    _make_jpeg(src)
    dst = tmp_path / "deep" / "nested" / "out.jpg"

    overlay_grid(src, dst)

    assert dst.exists()


def test_overlay_grid_validates_max_side(tmp_path: Path) -> None:
    src = tmp_path / "src.jpg"
    _make_jpeg(src)
    with pytest.raises(ValueError, match="max_side"):
        overlay_grid(src, tmp_path / "out.jpg", max_side=0)


def test_overlay_grid_validates_grid_step(tmp_path: Path) -> None:
    src = tmp_path / "src.jpg"
    _make_jpeg(src)
    with pytest.raises(ValueError, match="grid_step_pct"):
        overlay_grid(src, tmp_path / "out_a.jpg", grid_step_pct=0)
    with pytest.raises(ValueError, match="grid_step_pct"):
        overlay_grid(src, tmp_path / "out_b.jpg", grid_step_pct=51)


def test_overlay_grid_directory_processes_all_images(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    dst_dir = tmp_path / "dst"
    src_dir.mkdir()
    for i in range(3):
        _make_jpeg(src_dir / f"img_{i:03d}.jpg")

    results = overlay_grid_directory(src_dir, dst_dir)

    assert len(results) == 3
    for r in results:
        assert r.output.exists()
        assert r.output.parent == dst_dir
        assert r.output.suffix == ".jpg"


def test_overlay_grid_directory_creates_dst_dir(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    _make_jpeg(src_dir / "a.jpg")
    dst_dir = tmp_path / "new_dst"

    overlay_grid_directory(src_dir, dst_dir)

    assert dst_dir.is_dir()


def test_cli_crop_grid_smoke(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    dst_dir = tmp_path / "dst"
    src_dir.mkdir()
    for i in range(2):
        _make_jpeg(src_dir / f"p_{i}.jpg")

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "timelapse_agent",
            "crop-grid",
            str(src_dir),
            "--output-dir",
            str(dst_dir),
            "--max-side",
            "400",
        ],
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["status"] == "ok"
    assert payload["count"] == 2
    assert Path(payload["output_dir"]) == dst_dir
    assert all(Path(f).exists() for f in payload["files"])
