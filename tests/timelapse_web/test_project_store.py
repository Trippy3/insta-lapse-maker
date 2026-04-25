"""プロジェクトストアのラウンドトリップテスト。"""

from __future__ import annotations

from pathlib import Path

from timelapse_web.models import Clip, Project, TextOverlay
from timelapse_web.services import project_store


def test_save_and_load_roundtrip(tmp_path: Path):
    project = Project(
        name="例",
        clips=[
            Clip(id="c0", source_path="/tmp/a.jpg", order_index=0, duration_s=0.5),
            Clip(id="c1", source_path="/tmp/b.jpg", order_index=1, duration_s=0.8),
        ],
        overlays=[TextOverlay(text="こんにちは", start_s=0.0, end_s=1.0)],
    )
    dst = tmp_path / "out.tlproj.json"
    saved_path = project_store.save_project(project, dst)
    assert saved_path == dst.resolve()

    loaded = project_store.load_project(dst)
    assert loaded.name == "例"
    assert [c.id for c in loaded.clips] == ["c0", "c1"]
    assert loaded.overlays[0].text == "こんにちは"


def test_save_writes_atomically(tmp_path: Path):
    project = Project()
    dst = tmp_path / "atomic.tlproj.json"
    project_store.save_project(project, dst)
    assert dst.exists()
    # tmp ファイルが残っていないこと
    leftovers = list(tmp_path.glob(".tlproj-*.tmp"))
    assert leftovers == []


def test_load_missing_raises(tmp_path: Path):
    import pytest

    with pytest.raises(FileNotFoundError):
        project_store.load_project(tmp_path / "nope.tlproj.json")
