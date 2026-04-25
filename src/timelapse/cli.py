"""Typer CLI エントリポイント。"""

import tempfile
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from . import __version__
from .discovery import SortOrder, discover_images
from .encoder import encode
from .errors import ReferenceImageNotFoundError, TimelapseError
from .logging_setup import setup_logging
from .normalize import FitMode, normalize_all
from .reels_spec import REELS_FPS
from .similarity import (
    DEFAULT_HASH_THRESHOLD,
    HashCache,
    SimilarityStrategy,
    find_similar_images,
)
from .similarity_output import OutputFormat, format_results

app = typer.Typer(
    name="timelapse",
    help="絵画制作過程の写真から Instagram Reels 用タイムラプス動画を生成します。",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"timelapse {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-V", callback=version_callback, is_eager=True, help="バージョンを表示"),
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="詳細ログを表示")] = False,
) -> None:
    setup_logging(verbose=verbose)


@app.command()
def generate(
    input_dir: Annotated[Path, typer.Argument(help="写真が格納されたディレクトリ")],
    output: Annotated[Path, typer.Option("--output", "-o", help="出力 MP4 ファイルパス")] = Path("output.mp4"),
    duration: Annotated[float, typer.Option("--duration", "-d", help="1枚あたりの表示秒数")] = 0.3,
    fps: Annotated[float, typer.Option("--fps", help="フレームレート")] = float(REELS_FPS),
    sort: Annotated[SortOrder, typer.Option("--sort", "-s", help="ソート順")] = SortOrder.FILENAME,
    fit: Annotated[FitMode, typer.Option("--fit", "-f", help="アスペクト比調整モード (pad=黒帯, crop=中央クロップ)")] = FitMode.PAD,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="コマンドを表示するだけで実行しない")] = False,
) -> None:
    """写真ディレクトリから Instagram Reels 用タイムラプス動画を生成します。"""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("画像を検索中...", total=None)
            images = discover_images(input_dir, sort_order=sort)
            progress.update(task, description=f"[green]{len(images)} 枚の画像を発見")
            progress.stop_task(task)

            total_sec = len(images) * duration
            console.print(
                f"  画像数: [bold]{len(images)}[/bold]  "
                f"表示時間: [bold]{duration}s[/bold]/枚  "
                f"動画長: [bold]{total_sec:.1f}s[/bold]  "
                f"フィット: [bold]{fit.value}[/bold]  "
                f"ソート: [bold]{sort.value}[/bold]"
            )

            if dry_run:
                console.print("[yellow]ドライランモード: エンコードをスキップします。[/yellow]")
                raise typer.Exit()

            with tempfile.TemporaryDirectory(prefix="timelapse_") as tmp:
                task2 = progress.add_task("画像を正規化中...", total=None)
                normalized = normalize_all(images, Path(tmp) / "frames", fit_mode=fit)
                progress.update(task2, description="[green]正規化完了", total=1, completed=1)

                task3 = progress.add_task("動画をエンコード中...", total=None)
                encode(images=normalized, output=output, duration_per_image=duration, fps=fps)
                progress.update(task3, description="[green]エンコード完了")

        console.print(f"\n[bold green]完了![/bold green] 出力ファイル: [bold]{output}[/bold]")

    except (TimelapseError, NotADirectoryError) as e:
        console.print(f"[bold red]エラー:[/bold red] {e}")
        raise typer.Exit(code=1) from e


@app.command("find-similar")
def find_similar(
    reference: Annotated[Path, typer.Argument(help="基準画像ファイルパス")],
    search_dir: Annotated[Path, typer.Argument(help="検索対象ディレクトリ")],
    threshold: Annotated[int, typer.Option("--threshold", "-t", help="ハミング距離しきい値 (0-64, default: 10)")] = DEFAULT_HASH_THRESHOLD,
    strategy: Annotated[SimilarityStrategy, typer.Option("--strategy", "-S", help="類似度計算戦略")] = SimilarityStrategy.PHASH,
    fmt: Annotated[OutputFormat, typer.Option("--format", "-F", help="出力形式 (plain/json/scored)")] = OutputFormat.PLAIN,
    sort: Annotated[str, typer.Option("--sort", help="ソート順 (similarity/filename)")] = "similarity",
    recursive: Annotated[bool, typer.Option("--recursive", "-r", help="サブディレクトリも再帰検索")] = False,
    max_workers: Annotated[Optional[int], typer.Option("--max-workers", help="並列ワーカー数")] = None,
    use_cache: Annotated[bool, typer.Option("--cache", help="ハッシュキャッシュを有効化")] = False,
    cache_dir: Annotated[Optional[Path], typer.Option("--cache-dir", help="キャッシュ保存先ディレクトリ")] = None,
) -> None:
    """指定画像に類似した画像をフォルダから検索してパス一覧を出力します（結果はstdout、進捗はstderr）。"""
    err_console = Console(stderr=True)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=Console(stderr=True),
            transient=True,
        ) as progress:
            task = progress.add_task("候補画像を検索中...", total=None)
            candidates = discover_images(search_dir, recursive=recursive)
            ref_abs = reference.resolve()
            candidates = [p for p in candidates if p.resolve() != ref_abs]
            progress.update(task, description=f"[green]{len(candidates)} 枚の候補画像を発見")

        cache: Optional[HashCache] = HashCache(cache_dir) if use_cache else None

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=Console(stderr=True),
            transient=True,
        ) as progress:
            task2 = progress.add_task("類似度を計算中...", total=len(candidates))

            def on_progress(n: int) -> None:
                progress.update(task2, completed=n)

            results = find_similar_images(
                reference=reference,
                candidates=candidates,
                strategy=strategy,
                threshold=threshold,
                max_workers=max_workers,
                cache=cache,
                on_progress=on_progress,
            )

        if sort == "similarity":
            results = sorted(results, key=lambda r: (-r.score, str(r.path)))
        else:
            results = sorted(results, key=lambda r: str(r.path))

        output = format_results(results, fmt)
        if output:
            typer.echo(output)

        err_console.print(f"\n[bold green]{len(results)} 枚の類似画像を発見[/bold green]")

    except ReferenceImageNotFoundError as e:
        err_console.print(f"[bold red]エラー:[/bold red] {e}")
        raise typer.Exit(code=1) from e
    except (TimelapseError, NotADirectoryError) as e:
        err_console.print(f"[bold red]エラー:[/bold red] {e}")
        raise typer.Exit(code=1) from e
