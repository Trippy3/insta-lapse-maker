"""レンダ API。"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..config import AppConfig
from ..models import JobKind, RenderJob
from ..services.filtergraph import RenderTarget
from ..services.job_queue import JobQueue
from .deps import get_config, get_job_queue, get_projects

router = APIRouter(prefix="/api/render", tags=["render"])


class RenderRequest(BaseModel):
    project_id: str
    kind: JobKind = JobKind.FINAL
    output_path: str | None = None  # None の場合はキャッシュディレクトリに生成


@router.post("", response_model=RenderJob)
def submit_render(
    body: RenderRequest,
    projects: Annotated[dict, Depends(get_projects)],
    queue: Annotated[JobQueue, Depends(get_job_queue)],
    config: Annotated[AppConfig, Depends(get_config)],
) -> RenderJob:
    project = projects.get(body.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    if not project.clips:
        raise HTTPException(status_code=400, detail="clips が空です")

    if body.kind == JobKind.PROXY:
        target = RenderTarget.proxy(project)
        default_dir = config.cache_root / "proxy"
    else:
        target = RenderTarget.from_project(project)
        default_dir = config.cache_root / "renders"

    output = Path(body.output_path).expanduser() if body.output_path else None
    if output is None:
        default_dir.mkdir(parents=True, exist_ok=True)
        output = default_dir / f"{project.id}_{body.kind.value}.mp4"

    return queue.submit(project, target, output, kind=body.kind)


@router.get("/{job_id}", response_model=RenderJob)
def get_job(
    job_id: str,
    queue: Annotated[JobQueue, Depends(get_job_queue)],
) -> RenderJob:
    job = queue.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.get("/{job_id}/file")
def download_output(
    job_id: str,
    queue: Annotated[JobQueue, Depends(get_job_queue)],
) -> FileResponse:
    job = queue.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if not job.output_path:
        raise HTTPException(status_code=404, detail="output 未生成")
    path = Path(job.output_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="output が見つかりません")
    return FileResponse(path, media_type="video/mp4", filename=path.name)
