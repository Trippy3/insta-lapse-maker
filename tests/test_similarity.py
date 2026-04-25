"""similarity モジュールのテスト。"""

from __future__ import annotations

import json
from pathlib import Path

import imagehash
import pytest
from PIL import Image

from timelapse.errors import InvalidImageError, ReferenceImageNotFoundError
from timelapse.similarity import (
    DEFAULT_HASH_THRESHOLD,
    HashCache,
    SimilarityResult,
    SimilarityStrategy,
    compute_hash,
    compute_histogram_correlation,
    find_similar_images,
)


# ── compute_hash ──────────────────────────────────────────────────────────────

class TestComputeHash:
    def test_same_image_same_hash(self, similarity_fixture):
        ref = similarity_fixture["reference"]
        h1 = compute_hash(ref, SimilarityStrategy.PHASH)
        h2 = compute_hash(ref, SimilarityStrategy.PHASH)
        assert h1 == h2

    def test_copy_has_distance_zero(self, similarity_fixture):
        ref = similarity_fixture["reference"]
        sim = similarity_fixture["similar"]
        h_ref = compute_hash(ref, SimilarityStrategy.PHASH)
        h_sim = compute_hash(sim, SimilarityStrategy.PHASH)
        assert (h_ref - h_sim) == 0

    def test_unrelated_has_large_distance(self, similarity_fixture):
        ref = similarity_fixture["reference"]
        unr = similarity_fixture["unrelated"]
        h_ref = compute_hash(ref, SimilarityStrategy.PHASH)
        h_unr = compute_hash(unr, SimilarityStrategy.PHASH)
        assert (h_ref - h_unr) > DEFAULT_HASH_THRESHOLD

    @pytest.mark.parametrize("strategy", [
        SimilarityStrategy.PHASH,
        SimilarityStrategy.DHASH,
        SimilarityStrategy.AHASH,
        SimilarityStrategy.COMBINED,
    ])
    def test_all_hash_strategies_return_imagehash(self, similarity_fixture, strategy):
        h = compute_hash(similarity_fixture["reference"], strategy)
        assert isinstance(h, imagehash.ImageHash)

    def test_histogram_strategy_raises(self, similarity_fixture):
        with pytest.raises(ValueError, match="HISTOGRAM"):
            compute_hash(similarity_fixture["reference"], SimilarityStrategy.HISTOGRAM)

    def test_invalid_image_raises(self, tmp_path: Path):
        broken = tmp_path / "broken.jpg"
        broken.write_bytes(b"not an image")
        with pytest.raises(InvalidImageError):
            compute_hash(broken, SimilarityStrategy.PHASH)


# ── compute_histogram_correlation ────────────────────────────────────────────

class TestHistogramCorrelation:
    def test_same_image_returns_one(self, similarity_fixture):
        ref = similarity_fixture["reference"]
        corr = compute_histogram_correlation(ref, ref)
        assert corr == pytest.approx(1.0, abs=1e-6)

    def test_copy_returns_near_one(self, similarity_fixture):
        ref = similarity_fixture["reference"]
        sim = similarity_fixture["similar"]
        corr = compute_histogram_correlation(ref, sim)
        assert corr > 0.99

    def test_unrelated_returns_lower_correlation(self, similarity_fixture):
        ref = similarity_fixture["reference"]
        unr = similarity_fixture["unrelated"]
        corr = compute_histogram_correlation(ref, unr)
        assert corr < 0.99

    def test_returns_float_in_range(self, similarity_fixture):
        ref = similarity_fixture["reference"]
        corr = compute_histogram_correlation(ref, ref)
        assert 0.0 <= corr <= 1.0


# ── find_similar_images ───────────────────────────────────────────────────────

class TestFindSimilarImages:
    def test_finds_identical_copy(self, similarity_fixture):
        results = find_similar_images(
            reference=similarity_fixture["reference"],
            candidates=[similarity_fixture["similar"]],
            strategy=SimilarityStrategy.PHASH,
            threshold=0,
        )
        assert len(results) == 1
        assert results[0].path == similarity_fixture["similar"]
        assert results[0].distance == 0
        assert results[0].score == pytest.approx(1.0)

    def test_excludes_unrelated_with_strict_threshold(self, similarity_fixture):
        results = find_similar_images(
            reference=similarity_fixture["reference"],
            candidates=[similarity_fixture["unrelated"]],
            strategy=SimilarityStrategy.PHASH,
            threshold=0,
        )
        assert len(results) == 0

    def test_finds_similar_excludes_unrelated(self, similarity_fixture):
        candidates = [similarity_fixture["similar"], similarity_fixture["unrelated"]]
        results = find_similar_images(
            reference=similarity_fixture["reference"],
            candidates=candidates,
            strategy=SimilarityStrategy.PHASH,
            threshold=DEFAULT_HASH_THRESHOLD,
        )
        paths = [r.path for r in results]
        assert similarity_fixture["similar"] in paths
        assert similarity_fixture["unrelated"] not in paths

    def test_reference_not_found_raises(self, tmp_path: Path, similarity_fixture):
        with pytest.raises(ReferenceImageNotFoundError):
            find_similar_images(
                reference=tmp_path / "nonexistent.jpg",
                candidates=[similarity_fixture["similar"]],
            )

    def test_broken_candidate_is_skipped(self, tmp_path: Path, similarity_fixture):
        broken = tmp_path / "broken.jpg"
        broken.write_bytes(b"not an image")
        results = find_similar_images(
            reference=similarity_fixture["reference"],
            candidates=[broken, similarity_fixture["similar"]],
            threshold=0,
        )
        paths = [r.path for r in results]
        assert broken not in paths
        assert similarity_fixture["similar"] in paths

    def test_empty_candidates_returns_empty(self, similarity_fixture):
        results = find_similar_images(
            reference=similarity_fixture["reference"],
            candidates=[],
        )
        assert results == []

    def test_on_progress_callback_called(self, similarity_fixture):
        calls = []
        find_similar_images(
            reference=similarity_fixture["reference"],
            candidates=[similarity_fixture["similar"], similarity_fixture["unrelated"]],
            threshold=DEFAULT_HASH_THRESHOLD,
            on_progress=calls.append,
        )
        assert len(calls) == 2

    def test_histogram_strategy(self, similarity_fixture):
        results = find_similar_images(
            reference=similarity_fixture["reference"],
            candidates=[similarity_fixture["similar"]],
            strategy=SimilarityStrategy.HISTOGRAM,
            histogram_threshold=0.99,
        )
        assert len(results) == 1
        assert results[0].distance is None
        assert 0.0 <= results[0].score <= 1.0

    def test_result_is_frozen_dataclass(self, similarity_fixture):
        results = find_similar_images(
            reference=similarity_fixture["reference"],
            candidates=[similarity_fixture["similar"]],
            threshold=0,
        )
        assert len(results) == 1
        with pytest.raises((AttributeError, TypeError)):
            results[0].score = 0.5  # type: ignore[misc]

    def test_parallel_execution_returns_correct_results(self, similarity_fixture):
        candidates = [similarity_fixture["similar"]] * 4
        results = find_similar_images(
            reference=similarity_fixture["reference"],
            candidates=candidates,
            threshold=0,
            max_workers=2,
        )
        assert len(results) == 4


# ── HashCache ────────────────────────────────────────────────────────────────

class TestHashCache:
    def test_miss_returns_none(self, tmp_path: Path, similarity_fixture):
        cache = HashCache(tmp_path)
        result = cache.get(similarity_fixture["reference"], SimilarityStrategy.PHASH)
        assert result is None

    def test_set_then_get_returns_hash(self, tmp_path: Path, similarity_fixture):
        cache = HashCache(tmp_path)
        h = compute_hash(similarity_fixture["reference"], SimilarityStrategy.PHASH)
        cache.set(similarity_fixture["reference"], SimilarityStrategy.PHASH, h)
        cached = cache.get(similarity_fixture["reference"], SimilarityStrategy.PHASH)
        assert cached is not None
        assert (h - cached) == 0

    def test_save_and_reload(self, tmp_path: Path, similarity_fixture):
        cache1 = HashCache(tmp_path)
        h = compute_hash(similarity_fixture["reference"], SimilarityStrategy.PHASH)
        cache1.set(similarity_fixture["reference"], SimilarityStrategy.PHASH, h)
        cache1.save()

        cache2 = HashCache(tmp_path)
        cached = cache2.get(similarity_fixture["reference"], SimilarityStrategy.PHASH)
        assert cached is not None
        assert (h - cached) == 0

    def test_cache_file_path(self, tmp_path: Path):
        cache = HashCache(tmp_path)
        assert cache._cache_file == tmp_path / "hashes.json"

    def test_default_cache_dir(self):
        cache = HashCache()
        from pathlib import Path
        assert ".cache" in str(cache._cache_file)

    def test_stale_mtime_invalidates_cache(self, tmp_path: Path, similarity_fixture):
        cache = HashCache(tmp_path)
        ref = similarity_fixture["reference"]
        h = compute_hash(ref, SimilarityStrategy.PHASH)
        cache.set(ref, SimilarityStrategy.PHASH, h)

        # 強制的に mtime を変更
        import time
        time.sleep(0.01)
        ref.touch()

        result = cache.get(ref, SimilarityStrategy.PHASH)
        assert result is None

    def test_corrupted_cache_file_handled_gracefully(self, tmp_path: Path):
        cache_file = tmp_path / "hashes.json"
        cache_file.write_text("{ invalid json }")
        cache = HashCache(tmp_path)
        assert cache._data == {}

    def test_cache_used_in_find_similar(self, tmp_path: Path, similarity_fixture):
        cache = HashCache(tmp_path)
        results = find_similar_images(
            reference=similarity_fixture["reference"],
            candidates=[similarity_fixture["similar"]],
            threshold=0,
            cache=cache,
        )
        assert (tmp_path / "hashes.json").exists()
        assert len(results) == 1
