"""FS ブラウザ API (api/fs.py) の smoke テスト。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from timelapse_web.config import AppConfig
from timelapse_web.main import create_app


@pytest.fixture()
def fs_client(tmp_path: Path) -> TestClient:
    # 許可ルートを tmp_path に限定
    cfg = AppConfig(
        cache_root=tmp_path / "cache",
        host="127.0.0.1",
        port=0,
        static_root=None,
        fs_roots=(tmp_path.resolve(),),
    )
    app = create_app(cfg)
    return TestClient(app)


def test_home_returns_root(fs_client: TestClient, tmp_path: Path):
    r = fs_client.get("/api/fs/home")
    assert r.status_code == 200, r.text
    body = r.json()
    # ホームはルート外のことが多いので、roots の最初のもの (tmp_path) にフォールバックする
    assert str(tmp_path.resolve()) in body["roots"]
    # home はルート配下のどこかに収まっている
    assert any(body["home"].startswith(r) for r in body["roots"])


def test_browse_lists_dirs_and_images(fs_client: TestClient, tmp_path: Path):
    (tmp_path / "sub").mkdir()
    Image.new("RGB", (10, 10), (0, 0, 0)).save(tmp_path / "a.jpg")
    (tmp_path / "readme.txt").write_text("hi")

    r = fs_client.get(f"/api/fs/browse?path={tmp_path}")
    assert r.status_code == 200, r.text
    body = r.json()
    names_by_type = {e["type"]: [x["name"] for x in body["entries"] if x["type"] == e["type"]] for e in body["entries"]}
    assert "sub" in names_by_type.get("dir", [])
    assert "a.jpg" in names_by_type.get("image", [])
    # 非画像ファイルは省く
    assert "readme.txt" not in [e["name"] for e in body["entries"]]


def test_browse_rejects_outside_roots(fs_client: TestClient):
    # ルートは tmp_path のみ。/etc を直叩きしても 403
    r = fs_client.get("/api/fs/browse?path=/etc")
    assert r.status_code == 403, r.text


def test_browse_rejects_traversal(fs_client: TestClient, tmp_path: Path):
    # resolve 後にルート外へ逃げるトラバーサルも 403
    escape = f"{tmp_path}/../../../../../../etc"
    r = fs_client.get(f"/api/fs/browse?path={escape}")
    assert r.status_code == 403


def test_browse_missing_returns_404(fs_client: TestClient, tmp_path: Path):
    r = fs_client.get(f"/api/fs/browse?path={tmp_path / 'nope'}")
    assert r.status_code == 404


def test_browse_file_returns_400(fs_client: TestClient, tmp_path: Path):
    f = tmp_path / "a.txt"
    f.write_text("hi")
    r = fs_client.get(f"/api/fs/browse?path={f}")
    assert r.status_code == 400


def test_browse_hidden_files_toggle(fs_client: TestClient, tmp_path: Path):
    (tmp_path / ".secret").mkdir()
    (tmp_path / "visible").mkdir()

    r = fs_client.get(f"/api/fs/browse?path={tmp_path}")
    names = [e["name"] for e in r.json()["entries"]]
    assert ".secret" not in names
    assert "visible" in names

    r = fs_client.get(f"/api/fs/browse?path={tmp_path}&show_hidden=true")
    names = [e["name"] for e in r.json()["entries"]]
    assert ".secret" in names


def test_browse_has_images_hint(fs_client: TestClient, tmp_path: Path):
    shots = tmp_path / "shots"
    shots.mkdir()
    Image.new("RGB", (10, 10), (0, 0, 0)).save(shots / "photo.jpg")
    (tmp_path / "empty").mkdir()

    r = fs_client.get(f"/api/fs/browse?path={tmp_path}")
    by_name = {e["name"]: e for e in r.json()["entries"]}
    assert by_name["shots"]["has_images"] is True
    assert by_name["empty"]["has_images"] is False


def test_browse_match_ext_includes_project_files(fs_client: TestClient, tmp_path: Path):
    (tmp_path / "foo.tlproj.json").write_text("{}")
    (tmp_path / "note.txt").write_text("hi")

    # match_ext なし → プロジェクトファイルは省かれる
    r = fs_client.get(f"/api/fs/browse?path={tmp_path}")
    names = [e["name"] for e in r.json()["entries"]]
    assert "foo.tlproj.json" not in names

    # match_ext あり → 表示される (type=file)
    r = fs_client.get(f"/api/fs/browse?path={tmp_path}&match_ext=.tlproj.json")
    body = r.json()
    by_name = {e["name"]: e for e in body["entries"]}
    assert "foo.tlproj.json" in by_name
    assert by_name["foo.tlproj.json"]["type"] == "file"
    # 無関係ファイルは相変わらず非表示
    assert "note.txt" not in by_name


def test_browse_parent_stops_at_root(fs_client: TestClient, tmp_path: Path):
    # tmp_path のルート自体では parent=None
    r = fs_client.get(f"/api/fs/browse?path={tmp_path}")
    assert r.json()["parent"] is None

    # サブディレクトリでは parent が tmp_path になる
    sub = tmp_path / "x"
    sub.mkdir()
    r = fs_client.get(f"/api/fs/browse?path={sub}")
    assert r.json()["parent"] == str(tmp_path.resolve())


def test_native_available_flag_is_boolean(fs_client: TestClient):
    r = fs_client.get("/api/fs/native-available")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["available"], bool)
    # available=False のときは理由が reason に入る
    if not body["available"]:
        assert isinstance(body["reason"], str) and body["reason"]
    else:
        assert body["reason"] is None


def test_native_available_reason_when_no_display(
    fs_client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    r = fs_client.get("/api/fs/native-available")
    body = r.json()
    # Linux 前提のテスト (sys.platform == "linux")
    import sys

    if sys.platform.startswith("linux"):
        assert body["available"] is False
        assert "DISPLAY" in body["reason"]


def _raise_unavailable(*_args, **_kwargs):
    from timelapse_web.services.native_picker import NativePickerUnavailable

    raise NativePickerUnavailable("test: forced unavailable")


def test_native_pick_501_when_unavailable(
    fs_client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    # pick が Unavailable を投げれば 501 に変換される
    monkeypatch.setattr("timelapse_web.api.fs.native_pick", _raise_unavailable)
    r = fs_client.post("/api/fs/native-pick", json={"mode": "directory"})
    assert r.status_code == 501
    assert "test: forced unavailable" in r.json()["detail"]


def test_native_pick_returns_cancelled_when_worker_returns_none(
    fs_client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    # ユーザーがダイアログをキャンセル
    monkeypatch.setattr("timelapse_web.api.fs.native_pick", lambda req: None)
    r = fs_client.post("/api/fs/native-pick", json={"mode": "directory"})
    assert r.status_code == 200
    body = r.json()
    assert body["cancelled"] is True
    assert body["path"] is None


def test_native_pick_enforces_fs_roots(
    fs_client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    # tmp_path の外の /etc をユーザーが選んだと仮定 → 403
    monkeypatch.setattr("timelapse_web.api.fs.native_pick", lambda req: "/etc")
    r = fs_client.post("/api/fs/native-pick", json={"mode": "directory"})
    assert r.status_code == 403


def test_native_pick_returns_resolved_path_when_within_roots(
    fs_client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    sub = tmp_path / "photos"
    sub.mkdir()
    monkeypatch.setattr("timelapse_web.api.fs.native_pick", lambda req: str(sub))
    r = fs_client.post("/api/fs/native-pick", json={"mode": "directory"})
    assert r.status_code == 200
    assert r.json()["path"] == str(sub.resolve())
    assert r.json()["cancelled"] is False


def test_native_available_includes_backend(fs_client: TestClient):
    r = fs_client.get("/api/fs/native-available")
    body = r.json()
    if body["available"]:
        assert body["backend"] in {"zenity", "tkinter"}
    else:
        assert body["backend"] is None
