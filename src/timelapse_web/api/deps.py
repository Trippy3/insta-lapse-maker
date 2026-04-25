"""FastAPI 依存注入ヘルパ。"""

from __future__ import annotations

from fastapi import Request

from ..config import AppConfig
from ..services.job_queue import JobQueue


def get_config(request: Request) -> AppConfig:
    return request.app.state.config


def get_job_queue(request: Request) -> JobQueue:
    return request.app.state.job_queue


def get_projects(request: Request) -> dict:
    """プロセス内プロジェクトメモリ (id -> Project)。"""
    return request.app.state.projects
