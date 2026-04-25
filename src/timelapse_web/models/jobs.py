"""レンダジョブモデル。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class JobKind(str, Enum):
    PROXY = "proxy"
    FINAL = "final"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


def _new_job_id() -> str:
    return f"job_{uuid.uuid4().hex[:12]}"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class RenderJob(BaseModel):
    id: str = Field(default_factory=_new_job_id)
    project_id: str
    kind: JobKind = JobKind.FINAL
    status: JobStatus = JobStatus.QUEUED
    progress: float = Field(ge=0.0, le=1.0, default=0.0)
    output_path: str | None = None
    error: str | None = None
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)

    def touch(self) -> None:
        # 不変ではないが小規模なため直接書き換え (API 境界では新インスタンスを返す)
        object.__setattr__(self, "updated_at", _utcnow())
