"""timelapse-agent CLI: inspect / scaffold / render の 3 サブコマンド。

起動方法:
    uv run python -m timelapse_agent <subcommand>
    uv run timelapse-agent <subcommand>  (pyproject.toml にスクリプト登録後)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import typer

from timelapse.discovery import SortOrder, discover_images
from timelapse_web.models.project import TransitionKind
from timelapse_web.services.filtergraph import RenderTarget, plan_render
from timelapse_web.services.project_store import load_project, save_project
from timelapse_web.services.renderer import run_render

from .inspector import inspect_directory
from .planner import scaffold_project

app = typer.Typer(
    help="AI エージェント向け timelapse 動画制作 CLI",
    no_args_is_help=True,
)

_TRANSITION_CHOICES = [k.value for k in TransitionKind]


@app.command()
def inspect(
    directory: Annotated[Path, typer.Argument(help="画像ディレクトリのパス")],
    sort: Annotated[str, typer.Option(help="並び順: filename | exif")] = "filename",
    recursive: Annotated[bool, typer.Option(help="サブディレクトリも対象にする")] = False,
) -> None:
    """画像メタデータ（サイズ・EXIF 日時・ファイル名）を JSON で stdout に出力する。"""
    sort_order = SortOrder.EXIF_DATETIME if sort == "exif" else SortOrder.FILENAME
    directory = directory.expanduser().resolve()
    infos = inspect_directory(directory, sort_order=sort_order, recursive=recursive)
    print(json.dumps(infos, ensure_ascii=False, indent=2), flush=True)


@app.command()
def scaffold(
    directory: Annotated[Path, typer.Argument(help="画像ディレクトリのパス")],
    output: Annotated[Path, typer.Option(help="出力する .tlproj.json のパス")],
    duration: Annotated[float, typer.Option(help="1 枚あたりの表示秒数")] = 0.5,
    transition: Annotated[str, typer.Option(help=f"トランジション種別: {_TRANSITION_CHOICES}")] = "cut",
    transition_duration: Annotated[float, typer.Option(help="トランジション秒数（cut では無視）")] = 0.0,
    sort: Annotated[str, typer.Option(help="並び順: filename | exif")] = "filename",
    recursive: Annotated[bool, typer.Option(help="サブディレクトリも対象にする")] = False,
    name: Annotated[str, typer.Option(help="プロジェクト名")] = "Untitled",
) -> None:
    """雛形プロジェクト (.tlproj.json) を生成する。カメラワークはあとで JSON を編集して追加できる。"""
    sort_order = SortOrder.EXIF_DATETIME if sort == "exif" else SortOrder.FILENAME
    directory = directory.expanduser().resolve()
    output = output.expanduser().resolve()

    kind_map = {k.value: k for k in TransitionKind}
    if transition not in kind_map:
        typer.echo(
            f"エラー: 不明なトランジション '{transition}'。使用可能: {_TRANSITION_CHOICES}",
            err=True,
        )
        raise typer.Exit(1)

    images = discover_images(directory, sort_order=sort_order, recursive=recursive)
    project = scaffold_project(
        image_paths=images,
        default_duration_s=duration,
        default_transition=kind_map[transition],
        transition_duration_s=transition_duration,
        name=name,
    )
    save_project(project, output)

    result = {
        "status": "ok",
        "output": str(output),
        "clip_count": len(project.clips),
        "total_duration_s": round(project.total_visible_duration_s(), 3),
    }
    print(json.dumps(result, ensure_ascii=False), flush=True)


@app.command()
def render(
    project_path: Annotated[Path, typer.Argument(help=".tlproj.json のパス")],
    output: Annotated[Path | None, typer.Option(help="出力 MP4 のパス（省略時はプロジェクトと同じ場所）")] = None,
    proxy: Annotated[bool, typer.Option(help="低解像度プロキシ (540×960 / 15fps) で生成")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="レンダせず計画情報のみ出力")] = False,
) -> None:
    """プロジェクトを動画にレンダする。進捗は stderr に 'progress=0.xx' 形式で出力する。"""
    project_path = project_path.expanduser().resolve()
    project = load_project(project_path)

    if proxy:
        target = RenderTarget(
            width=540,
            height=960,
            fps=15,
            video_bitrate="800k",
            video_maxrate="1200k",
            video_bufsize="2400k",
        )
    else:
        target = RenderTarget.from_project(project)

    plan = plan_render(project, target)

    if dry_run:
        result = {
            "status": "ok",
            "two_stage": plan.two_stage,
            "reason": plan.reason,
            "clip_count": len(project.clips),
            "duration_s": round(project.total_visible_duration_s(), 3),
        }
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return

    if output is None:
        output = project_path.with_suffix(".mp4")
    output = output.expanduser().resolve()

    def _on_progress(ratio: float) -> None:
        print(f"progress={ratio:.4f}", file=sys.stderr, flush=True)

    out = run_render(project, target, output, on_progress=_on_progress)
    result = {
        "status": "ok",
        "output": str(out),
        "duration_s": round(project.total_visible_duration_s(), 3),
    }
    print(json.dumps(result, ensure_ascii=False), flush=True)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
