"""類似画像検索結果の出力フォーマッタ。"""

from __future__ import annotations

import json
from enum import Enum

from .similarity import SimilarityResult


class OutputFormat(str, Enum):
    PLAIN = "plain"
    JSON = "json"
    SCORED = "scored"


def format_results(results: list[SimilarityResult], fmt: OutputFormat) -> str:
    """SimilarityResultのリストを指定形式に変換する。"""
    if fmt == OutputFormat.PLAIN:
        return "\n".join(str(r.path) for r in results)

    if fmt == OutputFormat.JSON:
        data = [
            {
                "path": str(r.path),
                "score": round(r.score, 4),
                "distance": r.distance,
            }
            for r in results
        ]
        return json.dumps(data, indent=2, ensure_ascii=False)

    # SCORED
    lines = []
    for r in results:
        dist_str = f"{r.distance:>3}" if r.distance is not None else "  -"
        lines.append(f"{r.score:.4f}  {dist_str}  {r.path}")
    return "\n".join(lines)
