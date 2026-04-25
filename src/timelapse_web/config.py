"""Web アプリのランタイム設定。環境変数から上書き可能。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _default_cache_root() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "timelapse-web"


def _default_fs_roots() -> tuple[Path, ...]:
    """FS ブラウザ API が走査を許可するディレクトリ群 (既定: ホーム)。"""
    return (Path.home().resolve(),)


def _parse_fs_roots(raw: str | None) -> tuple[Path, ...]:
    if not raw:
        return _default_fs_roots()
    roots: list[Path] = []
    for part in raw.split(os.pathsep):
        part = part.strip()
        if not part:
            continue
        p = Path(part).expanduser()
        try:
            roots.append(p.resolve())
        except OSError:
            continue
    return tuple(roots) if roots else _default_fs_roots()


@dataclass(frozen=True)
class AppConfig:
    cache_root: Path
    host: str
    port: int
    static_root: Path | None
    fs_roots: tuple[Path, ...] = ()

    @classmethod
    def from_env(cls) -> "AppConfig":
        cache_root = Path(os.environ.get("TIMELAPSE_WEB_CACHE", str(_default_cache_root())))
        host = os.environ.get("TIMELAPSE_WEB_HOST", "127.0.0.1")
        port = int(os.environ.get("TIMELAPSE_WEB_PORT", "8765"))
        static_env = os.environ.get("TIMELAPSE_WEB_STATIC")
        static_root = Path(static_env) if static_env else None
        fs_roots = _parse_fs_roots(os.environ.get("TIMELAPSE_WEB_FS_ROOTS"))
        return cls(
            cache_root=cache_root,
            host=host,
            port=port,
            static_root=static_root,
            fs_roots=fs_roots,
        )

    def ensure_dirs(self) -> None:
        (self.cache_root / "thumbs").mkdir(parents=True, exist_ok=True)
        (self.cache_root / "proxy").mkdir(parents=True, exist_ok=True)
        (self.cache_root / "renders").mkdir(parents=True, exist_ok=True)

    def effective_fs_roots(self) -> tuple[Path, ...]:
        """fs_roots が未設定のときはホームを既定とする。"""
        return self.fs_roots if self.fs_roots else _default_fs_roots()
