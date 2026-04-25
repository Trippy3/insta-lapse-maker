"""単一ワーカーのジョブキュー。

FFmpeg はシングルプロセスで走らせるため worker は 1。
SSE 配信のためにジョブ状態変更を asyncio.Event 経由で通知する。
"""

from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from ..models import JobKind, JobStatus, Project, RenderJob
from .filtergraph import RenderTarget
from .renderer import run_render

logger = logging.getLogger(__name__)

RenderFn = Callable[[Project, RenderTarget, Path, Callable[[float], None]], Path]


class JobQueue:
    """1 ワーカーで順次処理する簡易ジョブキュー。"""

    def __init__(self, render_fn: RenderFn | None = None) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="render")
        self._jobs: dict[str, RenderJob] = {}
        self._lock = threading.Lock()
        self._listeners: set[asyncio.Queue] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._render_fn: RenderFn = render_fn or run_render

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    # ---- ジョブ管理 ------------------------------------------------
    def submit(
        self,
        project: Project,
        target: RenderTarget,
        output: Path,
        kind: JobKind = JobKind.FINAL,
    ) -> RenderJob:
        job = RenderJob(project_id=project.id, kind=kind, output_path=str(output))
        with self._lock:
            self._jobs[job.id] = job
        self._executor.submit(self._run_job, job.id, project, target, output)
        self._broadcast(job)
        return job

    def get(self, job_id: str) -> RenderJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[RenderJob]:
        with self._lock:
            return list(self._jobs.values())

    # ---- イベント配信 (SSE) --------------------------------------
    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._listeners.add(q)
        # 既存ジョブのスナップショットを送信
        with self._lock:
            snapshot = list(self._jobs.values())
        for j in snapshot:
            q.put_nowait(j.model_dump(mode="json"))
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._listeners.discard(q)

    def _broadcast(self, job: RenderJob) -> None:
        payload = job.model_dump(mode="json")
        loop = self._loop
        if loop is None or not self._listeners:
            return
        # 別スレッド (render worker) から呼ぶ場合があるので loop 経由
        for q in list(self._listeners):
            try:
                loop.call_soon_threadsafe(_put_nowait_drop, q, payload)
            except RuntimeError:
                # loop が閉じている
                pass

    # ---- 実行 ---------------------------------------------------
    def _update(self, job_id: str, **changes) -> RenderJob | None:
        with self._lock:
            old = self._jobs.get(job_id)
            if old is None:
                return None
            new = old.model_copy(update=changes)
            new.touch()
            self._jobs[job_id] = new
            return new

    def _run_job(
        self,
        job_id: str,
        project: Project,
        target: RenderTarget,
        output: Path,
    ) -> None:
        job = self._update(job_id, status=JobStatus.RUNNING, progress=0.0)
        if job is not None:
            self._broadcast(job)

        def on_progress(p: float) -> None:
            updated = self._update(job_id, progress=p)
            if updated is not None:
                self._broadcast(updated)

        try:
            self._render_fn(project, target, output, on_progress)
        except Exception as exc:  # noqa: BLE001
            logger.exception("render failed: %s", exc)
            done = self._update(
                job_id,
                status=JobStatus.FAILED,
                error=str(exc)[-500:],
            )
            if done is not None:
                self._broadcast(done)
            return

        done = self._update(
            job_id, status=JobStatus.DONE, progress=1.0, output_path=str(output)
        )
        if done is not None:
            self._broadcast(done)


def _put_nowait_drop(q: asyncio.Queue, item: dict) -> None:
    """キューが満杯なら古いものを捨てて入れる。"""
    try:
        q.put_nowait(item)
    except asyncio.QueueFull:
        try:
            q.get_nowait()
        except asyncio.QueueEmpty:
            pass
        try:
            q.put_nowait(item)
        except asyncio.QueueFull:
            pass
