"""SSE でジョブ進捗を配信する。"""

from __future__ import annotations

import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ..services.job_queue import JobQueue
from .deps import get_job_queue

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("/jobs")
async def stream_jobs(
    request: Request,
    queue: Annotated[JobQueue, Depends(get_job_queue)],
) -> StreamingResponse:
    q = queue.subscribe()

    async def gen():
        try:
            yield "retry: 3000\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    item = await asyncio.wait_for(q.get(), timeout=15.0)
                    payload = json.dumps(item, ensure_ascii=False)
                    yield f"event: job\ndata: {payload}\n\n"
                except asyncio.TimeoutError:
                    # keep-alive コメント
                    yield ": ping\n\n"
        finally:
            queue.unsubscribe(q)

    return StreamingResponse(gen(), media_type="text/event-stream")
