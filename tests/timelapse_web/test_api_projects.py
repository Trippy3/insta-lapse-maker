"""プロジェクト API の smoke テスト (TestClient)。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from timelapse_web.config import AppConfig
from timelapse_web.main import create_app


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    cfg = AppConfig(cache_root=tmp_path / "cache", host="127.0.0.1", port=0, static_root=None)
    app = create_app(cfg)
    return TestClient(app)


def test_health(client: TestClient):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_create_get_update_project(client: TestClient):
    proj = {
        "schema_version": 1,
        "id": "proj_abc",
        "name": "test",
        "created_at": "2026-04-22T00:00:00+00:00",
        "updated_at": "2026-04-22T00:00:00+00:00",
        "output": {"width": 1080, "height": 1920, "fps": 30},
        "clips": [],
        "transitions": [],
        "overlays": [],
    }
    r = client.post("/api/projects", json=proj)
    assert r.status_code == 200, r.text
    assert r.json()["id"] == "proj_abc"

    r = client.get("/api/projects/proj_abc")
    assert r.status_code == 200
    assert r.json()["name"] == "test"

    proj["name"] = "renamed"
    r = client.put("/api/projects/proj_abc", json=proj)
    assert r.status_code == 200
    assert r.json()["name"] == "renamed"


def test_save_and_load_via_api(client: TestClient, tmp_path: Path):
    proj = {
        "schema_version": 1,
        "id": "proj_save",
        "name": "to-save",
        "created_at": "2026-04-22T00:00:00+00:00",
        "updated_at": "2026-04-22T00:00:00+00:00",
        "output": {"width": 1080, "height": 1920, "fps": 30},
        "clips": [],
        "transitions": [],
        "overlays": [],
    }
    client.post("/api/projects", json=proj)
    path = tmp_path / "saved.tlproj.json"
    r = client.post(f"/api/projects/{proj['id']}/save", json={"path": str(path)})
    assert r.status_code == 200, r.text
    assert path.exists()

    r = client.post("/api/projects/load", json={"path": str(path)})
    assert r.status_code == 200
    assert r.json()["project"]["name"] == "to-save"


def test_scan_empty_dir_returns_empty_list(client: TestClient, tmp_path: Path):
    # 画像が 1 枚もないディレクトリでも 200 + 空配列を返す
    empty = tmp_path / "empty"
    empty.mkdir()
    r = client.get(f"/api/media/scan?directory={empty}")
    assert r.status_code == 200
    assert r.json()["images"] == []


def test_scan_recursive_finds_nested_images(client: TestClient, tmp_path: Path):
    from PIL import Image

    nested = tmp_path / "parent" / "child"
    nested.mkdir(parents=True)
    Image.new("RGB", (10, 10), (255, 0, 0)).save(nested / "a.jpg")

    parent = tmp_path / "parent"
    # 非再帰では見つからない
    r = client.get(f"/api/media/scan?directory={parent}&recursive=false")
    assert r.status_code == 200
    assert r.json()["images"] == []
    # 再帰で見つかる
    r = client.get(f"/api/media/scan?directory={parent}&recursive=true")
    assert r.status_code == 200
    names = [i["filename"] for i in r.json()["images"]]
    assert names == ["a.jpg"]


def test_scan_missing_dir_returns_404(client: TestClient, tmp_path: Path):
    r = client.get(f"/api/media/scan?directory={tmp_path / 'nope'}")
    assert r.status_code == 404


def test_scan_file_path_returns_400(client: TestClient, tmp_path: Path):
    f = tmp_path / "a.txt"
    f.write_text("hi")
    r = client.get(f"/api/media/scan?directory={f}")
    assert r.status_code == 400


def test_render_fails_without_clips(client: TestClient):
    proj = {
        "schema_version": 1,
        "id": "proj_empty",
        "name": "empty",
        "created_at": "2026-04-22T00:00:00+00:00",
        "updated_at": "2026-04-22T00:00:00+00:00",
        "output": {"width": 1080, "height": 1920, "fps": 30},
        "clips": [],
        "transitions": [],
        "overlays": [],
    }
    client.post("/api/projects", json=proj)
    r = client.post("/api/render", json={"project_id": "proj_empty", "kind": "final"})
    assert r.status_code == 400
