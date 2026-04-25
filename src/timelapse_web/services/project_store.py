"""プロジェクト JSON の永続化。

Phase 1 はユーザー指定パス方式: save/load は絶対パスを受け取り、
アプリ管理ディレクトリは使わない。最近開いたパスだけはキャッシュに記録する。
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from ..models import Project

PROJECT_SUFFIX = ".tlproj.json"


def save_project(project: Project, path: Path) -> Path:
    """プロジェクトを指定パスに原子的に書き込む。"""
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    project_with_stamp = project.model_copy(
        update={"updated_at": datetime.now(timezone.utc).isoformat()}
    )
    payload = project_with_stamp.model_dump(mode="json")
    # 原子的書き込み: tmp に書いて rename
    fd, tmp_name = tempfile.mkstemp(
        prefix=".tlproj-", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_name, path)
    except Exception:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    return path


def load_project(path: Path) -> Project:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"プロジェクトファイルが見つかりません: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return Project.model_validate(data)
