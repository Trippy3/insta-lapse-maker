"""`timelapse-web` コマンドのエントリポイント。"""

from __future__ import annotations

import argparse
import logging

from .config import AppConfig


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="timelapse-web",
        description="timelapse 編集 Web アプリをローカル起動します。",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Web サーバーを起動")
    serve.add_argument("--host", default=None, help="バインドホスト (default: 127.0.0.1)")
    serve.add_argument("--port", type=int, default=None, help="ポート (default: 8765)")
    serve.add_argument("--reload", action="store_true", help="開発用リロード")
    serve.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.command == "serve":
        import uvicorn

        cfg = AppConfig.from_env()
        host = args.host or cfg.host
        port = args.port or cfg.port

        uvicorn.run(
            "timelapse_web.main:app",
            host=host,
            port=port,
            reload=args.reload,
            log_level="debug" if args.verbose else "info",
        )
