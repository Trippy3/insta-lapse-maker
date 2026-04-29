"""画像にグリッドを重ねて視認用サムネイルを生成するモジュール。

クロップ工程で絵画キャンバス (または切り出したい矩形) の輪郭の
正規化座標 (x, y, w, h) を人間が目視で読み取りやすくするための支援ツール。

絵画キャンバス・額縁・被写体の輪郭は、撮影アングルや背景の雑多さの影響で
自動エッジ検出 (Canny / Hough) では安定して取れないケースが多い。
このモジュールはグリッド (10% 刻みなど) を画像に重ねた縮小サムネイルを
生成し、視認 → 座標読み取り → JSON への記入、というワークフローを支える。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from timelapse.discovery import SortOrder, discover_images

_GRID_COLOR = (0, 255, 0)
_LABEL_COLOR = (0, 255, 255)


@dataclass(frozen=True)
class GridResult:
    """グリッド重畳済みサムネイルの生成結果。"""

    source: Path
    output: Path
    width: int
    height: int


def overlay_grid(
    src: Path,
    dst: Path,
    max_side: int = 900,
    grid_step_pct: int = 10,
) -> GridResult:
    """画像を縮小してグリッドを重ね、JPEG として保存する。

    Args:
        src: 入力画像のパス。
        dst: 出力画像のパス。親ディレクトリは自動作成。
        max_side: 出力画像の長辺 (px)。原画像より大きい値を指定しても拡大はしない。
        grid_step_pct: グリッド線の間隔 (% 単位、1〜50)。
                       10 なら 10/20/30/...90 の位置に縦横線とラベルが入る。

    Returns:
        GridResult: 出力画像のパスとサイズ。

    Raises:
        ValueError: max_side が非正値、または grid_step_pct が範囲外のとき。
    """
    if max_side <= 0:
        raise ValueError(f"max_side は正の整数を指定してください: {max_side}")
    if not 1 <= grid_step_pct <= 50:
        raise ValueError(
            f"grid_step_pct は 1〜50 の範囲で指定してください: {grid_step_pct}"
        )

    with Image.open(src) as img:
        canvas = img.convert("RGB")
        w, h = canvas.size
        scale = min(1.0, max_side / max(w, h))
        nw = max(1, int(round(w * scale)))
        nh = max(1, int(round(h * scale)))
        if (nw, nh) != (w, h):
            canvas = canvas.resize((nw, nh), Image.Resampling.LANCZOS)

        draw = ImageDraw.Draw(canvas)
        font = _safe_default_font()

        for i in range(grid_step_pct, 100, grid_step_pct):
            x = int(nw * i / 100)
            y = int(nh * i / 100)
            draw.line([(x, 0), (x, nh)], fill=_GRID_COLOR, width=1)
            draw.line([(0, y), (nw, y)], fill=_GRID_COLOR, width=1)
            label = str(i)
            draw.text((x + 2, 2), label, fill=_LABEL_COLOR, font=font)
            draw.text((2, y + 2), label, fill=_LABEL_COLOR, font=font)

        dst.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(dst, format="JPEG", quality=85)

    return GridResult(source=src, output=dst, width=nw, height=nh)


def overlay_grid_directory(
    src_dir: Path,
    dst_dir: Path,
    max_side: int = 900,
    grid_step_pct: int = 10,
    sort_order: SortOrder = SortOrder.FILENAME,
    recursive: bool = False,
) -> list[GridResult]:
    """ディレクトリ内の全画像にグリッドを重ねて dst_dir に保存する。

    出力ファイル名は元のステム + ".jpg" 固定 (HEIC 等もすべて JPEG として保存)。
    """
    images = discover_images(src_dir, sort_order=sort_order, recursive=recursive)
    dst_dir.mkdir(parents=True, exist_ok=True)
    results: list[GridResult] = []
    for src in images:
        dst = dst_dir / f"{src.stem}.jpg"
        results.append(
            overlay_grid(src, dst, max_side=max_side, grid_step_pct=grid_step_pct)
        )
    return results


def _safe_default_font() -> ImageFont.ImageFont:
    try:
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()
