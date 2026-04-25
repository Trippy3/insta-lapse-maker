"""find-similar CLIサブコマンドのテスト。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from timelapse.cli import app

runner = CliRunner()

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".bmp", ".tiff", ".tif"}


def _path_lines(output: str) -> list[str]:
    """出力から画像ファイルパス行のみを抽出する。"""
    return [
        l for l in output.strip().splitlines()
        if Path(l.strip()).suffix.lower() in IMAGE_EXTS
    ]


def _extract_json(output: str) -> str:
    """出力からJSON配列部分のみを抽出する。"""
    start = output.index("[")
    end = output.rindex("]") + 1
    return output[start:end]


class TestFindSimilarBasic:
    def test_finds_similar_plain_output(self, similarity_fixture):
        result = runner.invoke(app, [
            "find-similar",
            str(similarity_fixture["reference"]),
            str(similarity_fixture["search_dir"]),
            "--threshold", "0",
        ])
        assert result.exit_code == 0
        path_lines = _path_lines(result.output)
        assert len(path_lines) == 1
        assert "similar.png" in path_lines[0]

    def test_no_match_returns_empty_stdout(self, similarity_fixture):
        result = runner.invoke(app, [
            "find-similar",
            str(similarity_fixture["reference"]),
            str(similarity_fixture["search_dir"]),
            "--threshold", "0",
            "--strategy", "phash",
        ])
        assert result.exit_code == 0
        path_lines = _path_lines(result.output)
        assert "similar.png" in "\n".join(path_lines)
        assert "unrelated.png" not in "\n".join(path_lines)

    def test_json_format(self, similarity_fixture):
        result = runner.invoke(app, [
            "find-similar",
            str(similarity_fixture["reference"]),
            str(similarity_fixture["search_dir"]),
            "--threshold", "0",
            "--format", "json",
        ])
        assert result.exit_code == 0
        data = json.loads(_extract_json(result.output))
        assert isinstance(data, list)
        assert len(data) == 1
        assert "path" in data[0]
        assert "score" in data[0]
        assert "distance" in data[0]

    def test_scored_format(self, similarity_fixture):
        result = runner.invoke(app, [
            "find-similar",
            str(similarity_fixture["reference"]),
            str(similarity_fixture["search_dir"]),
            "--threshold", "0",
            "--format", "scored",
        ])
        assert result.exit_code == 0
        assert "1.0000" in result.output

    def test_sort_filename(self, similarity_fixture):
        result = runner.invoke(app, [
            "find-similar",
            str(similarity_fixture["reference"]),
            str(similarity_fixture["search_dir"]),
            "--threshold", "64",
            "--sort", "filename",
        ])
        assert result.exit_code == 0


class TestFindSimilarErrors:
    def test_nonexistent_reference_exits_with_code_1(self, similarity_fixture):
        result = runner.invoke(app, [
            "find-similar",
            "/nonexistent/ref.jpg",
            str(similarity_fixture["search_dir"]),
        ])
        assert result.exit_code == 1

    def test_nonexistent_search_dir_exits_with_code_1(self, similarity_fixture):
        result = runner.invoke(app, [
            "find-similar",
            str(similarity_fixture["reference"]),
            "/nonexistent/dir",
        ])
        assert result.exit_code == 1


class TestFindSimilarRecursive:
    def test_recursive_finds_in_subdir(self, similarity_fixture, tmp_path: Path):
        subdir = similarity_fixture["search_dir"] / "sub"
        subdir.mkdir()
        from PIL import Image
        Image.open(similarity_fixture["similar"]).save(subdir / "deep.png", format="PNG")

        result = runner.invoke(app, [
            "find-similar",
            str(similarity_fixture["reference"]),
            str(similarity_fixture["search_dir"]),
            "--threshold", "0",
            "--recursive",
        ])
        assert result.exit_code == 0
        assert "deep.png" in "\n".join(_path_lines(result.output))

    def test_non_recursive_does_not_find_in_subdir(self, similarity_fixture, tmp_path: Path):
        subdir = similarity_fixture["search_dir"] / "sub2"
        subdir.mkdir()
        from PIL import Image
        Image.open(similarity_fixture["similar"]).save(subdir / "deep.png", format="PNG")

        result = runner.invoke(app, [
            "find-similar",
            str(similarity_fixture["reference"]),
            str(similarity_fixture["search_dir"]),
            "--threshold", "0",
        ])
        assert result.exit_code == 0
        assert "deep.png" not in "\n".join(_path_lines(result.output))


class TestFindSimilarCache:
    def test_cache_creates_json_file(self, similarity_fixture, tmp_path: Path):
        cache_dir = tmp_path / "cache"
        result = runner.invoke(app, [
            "find-similar",
            str(similarity_fixture["reference"]),
            str(similarity_fixture["search_dir"]),
            "--threshold", "0",
            "--cache",
            "--cache-dir", str(cache_dir),
        ])
        assert result.exit_code == 0
        assert (cache_dir / "hashes.json").exists()

    def test_second_run_with_cache_succeeds(self, similarity_fixture, tmp_path: Path):
        cache_dir = tmp_path / "cache"
        for _ in range(2):
            result = runner.invoke(app, [
                "find-similar",
                str(similarity_fixture["reference"]),
                str(similarity_fixture["search_dir"]),
                "--threshold", "0",
                "--cache",
                "--cache-dir", str(cache_dir),
            ])
            assert result.exit_code == 0


class TestFindSimilarReferenceExcluded:
    def test_reference_in_search_dir_is_excluded(self, tmp_path: Path):
        """検索ディレクトリに基準画像自体があっても結果から除外される。"""
        from conftest import _make_structured_image
        search_dir = tmp_path / "search"
        search_dir.mkdir()
        ref = _make_structured_image(search_dir / "ref.png")

        result = runner.invoke(app, [
            "find-similar",
            str(ref),
            str(search_dir),
            "--threshold", "64",
        ])
        assert result.exit_code == 0
        assert "ref.png" not in "\n".join(_path_lines(result.output))
