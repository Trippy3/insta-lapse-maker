"""FastAPI アプリのファクトリ。"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import events as events_api
from .api import fs as fs_api
from .api import media as media_api
from .api import projects as projects_api
from .api import render as render_api
from .config import AppConfig
from .services.job_queue import JobQueue
from .services.native_picker import (
    active_backend as _native_active_backend,
    unavailable_reason as _native_unavailable_reason,
)

# uvicorn が拾って `INFO:     ...` 形式で出すロガー名
logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    app.state.job_queue.bind_loop(loop)
    yield


def create_app(config: AppConfig | None = None) -> FastAPI:
    cfg = config or AppConfig.from_env()
    cfg.ensure_dirs()

    app = FastAPI(
        title="timelapse-web",
        version="0.1.0",
        lifespan=_lifespan,
    )
    # ローカル専用だが Vite 開発サーバー (5173) からのプロキシ未経由アクセスに備え
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    app.state.config = cfg
    app.state.projects = {}  # id -> Project (メモリ内)
    app.state.job_queue = JobQueue()

    native_reason = _native_unavailable_reason()
    if native_reason is None:
        logger.info(
            "ネイティブファイルダイアログ: 有効 (バックエンド=%s)",
            _native_active_backend(),
        )
    else:
        logger.warning(
            "ネイティブファイルダイアログ: 無効 (理由: %s) — Web 内蔵ピッカーを使います",
            native_reason,
        )

    app.include_router(projects_api.router)
    app.include_router(media_api.router)
    app.include_router(render_api.router)
    app.include_router(events_api.router)
    app.include_router(fs_api.router)

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True, "cache_root": str(cfg.cache_root)}

    # フロントエンドの静的ファイル配信 (ビルド後の web/dist)
    static_root = _resolve_static_root(cfg)
    if static_root is not None and static_root.is_dir():
        app.mount("/", StaticFiles(directory=str(static_root), html=True), name="static")
    else:
        logger.info(
            "静的ディレクトリが見つかりません (フロントは Vite dev サーバーから提供): %s",
            static_root,
        )

    return app


def _resolve_static_root(cfg: AppConfig) -> Path | None:
    if cfg.static_root is not None:
        return cfg.static_root
    # リポジトリ同梱の web/dist を既定で探す
    here = Path(__file__).resolve()
    candidate = here.parent.parent.parent / "web" / "dist"
    if candidate.is_dir():
        return candidate
    return None


app = create_app()
