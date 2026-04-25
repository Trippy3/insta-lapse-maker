"""similarity_output モジュールのテスト。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from timelapse.similarity import SimilarityResult
from timelapse.similarity_output import OutputFormat, format_results


@pytest.fixture()
def results_with_distance():
    return [
        SimilarityResult(path=Path("/photos/a.jpg"), score=1.0, distance=0),
        SimilarityResult(path=Path("/photos/b.jpg"), score=0.9375, distance=4),
    ]


@pytest.fixture()
def results_without_distance():
    return [
        SimilarityResult(path=Path("/photos/a.jpg"), score=0.95, distance=None),
    ]


class TestFormatResultsPlain:
    def test_one_path_per_line(self, results_with_distance):
        output = format_results(results_with_distance, OutputFormat.PLAIN)
        lines = output.splitlines()
        assert len(lines) == 2
        assert lines[0] == "/photos/a.jpg"
        assert lines[1] == "/photos/b.jpg"

    def test_empty_results_returns_empty_string(self):
        assert format_results([], OutputFormat.PLAIN) == ""


class TestFormatResultsJson:
    def test_valid_json(self, results_with_distance):
        output = format_results(results_with_distance, OutputFormat.JSON)
        data = json.loads(output)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_fields_present(self, results_with_distance):
        data = json.loads(format_results(results_with_distance, OutputFormat.JSON))
        for item in data:
            assert "path" in item
            assert "score" in item
            assert "distance" in item

    def test_score_rounded_to_4_decimals(self, results_with_distance):
        data = json.loads(format_results(results_with_distance, OutputFormat.JSON))
        for item in data:
            assert len(str(item["score"]).split(".")[-1]) <= 4

    def test_distance_none_preserved(self, results_without_distance):
        data = json.loads(format_results(results_without_distance, OutputFormat.JSON))
        assert data[0]["distance"] is None

    def test_empty_results_valid_json(self):
        output = format_results([], OutputFormat.JSON)
        assert json.loads(output) == []


class TestFormatResultsScored:
    def test_contains_score_distance_path(self, results_with_distance):
        output = format_results(results_with_distance, OutputFormat.SCORED)
        lines = output.splitlines()
        assert len(lines) == 2
        assert "1.0000" in lines[0]
        assert "/photos/a.jpg" in lines[0]

    def test_none_distance_shows_dash(self, results_without_distance):
        output = format_results(results_without_distance, OutputFormat.SCORED)
        assert "  -" in output

    def test_empty_results_returns_empty_string(self):
        assert format_results([], OutputFormat.SCORED) == ""
