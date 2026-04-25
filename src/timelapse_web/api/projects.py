"""プロジェクト CRUD + ファイル保存/読込 API。"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from ..models import Project
from ..services import project_store
from .deps import get_projects

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectPathBody(BaseModel):
    path: str


class ProjectWithPath(BaseModel):
    project: Project
    path: str | None = None


@router.post("", response_model=Project)
def create_project(
    project: Annotated[Project, Body()],
    projects: Annotated[dict, Depends(get_projects)],
) -> Project:
    projects[project.id] = project
    return project


@router.get("/{project_id}", response_model=Project)
def get_project(
    project_id: str,
    projects: Annotated[dict, Depends(get_projects)],
) -> Project:
    p = projects.get(project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="project not found")
    return p


@router.put("/{project_id}", response_model=Project)
def update_project(
    project_id: str,
    project: Annotated[Project, Body()],
    projects: Annotated[dict, Depends(get_projects)],
) -> Project:
    if project.id != project_id:
        raise HTTPException(status_code=400, detail="project.id が URL と一致しません")
    projects[project_id] = project
    return project


@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    projects: Annotated[dict, Depends(get_projects)],
) -> dict:
    projects.pop(project_id, None)
    return {"ok": True}


@router.post("/{project_id}/save", response_model=ProjectWithPath)
def save_project(
    project_id: str,
    body: ProjectPathBody,
    projects: Annotated[dict, Depends(get_projects)],
) -> ProjectWithPath:
    p = projects.get(project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="project not found")
    saved_path = project_store.save_project(p, Path(body.path))
    return ProjectWithPath(project=p, path=str(saved_path))


@router.post("/load", response_model=ProjectWithPath)
def load_project(
    body: ProjectPathBody,
    projects: Annotated[dict, Depends(get_projects)],
) -> ProjectWithPath:
    try:
        loaded = project_store.load_project(Path(body.path))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"読み込み失敗: {exc}") from exc
    projects[loaded.id] = loaded
    return ProjectWithPath(project=loaded, path=str(Path(body.path).expanduser().resolve()))
