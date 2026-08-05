"""Unit tests for the pure-python formula functions in
app/services/analytics_service.py, using small fixed input arrays and
asserting exact formula outputs against the worked examples from the spec.
"""
import pytest

from app.services.analytics_service import (
    compute_fatigue_buckets,
    compute_lvi_rows,
    compute_mastery_rows,
    compute_qdi_rows,
)


class TestLearningVelocityIndex:
    def test_worked_example(self):
        # user: accuracy=0.80 (8/10), mean=18000ms, std=6000ms
        # two extra cohort members purely to establish the [10000,30000]
        # clipped range referenced by the worked example.
        rows = [
            {"user_id": "u1", "total": 10, "correct": 8, "avg_time_ms": 18000, "std_time_ms": 6000},
            {"user_id": "u2", "total": 10, "correct": 5, "avg_time_ms": 10000, "std_time_ms": 2000},
            {"user_id": "u3", "total": 10, "correct": 5, "avg_time_ms": 30000, "std_time_ms": 2000},
        ]
        results = compute_lvi_rows(rows)
        u1 = next(r for r in results if r["user_id"] == "u1")

        assert u1["accuracy"] == pytest.approx(0.80)
        assert u1["consistency_score"] == pytest.approx(0.75, abs=1e-3)
        # LVI = 100*(0.5*0.80 + 0.3*0.60 + 0.2*0.75) = 73.0
        assert u1["lvi"] == pytest.approx(73.0, abs=0.1)

    def test_ranked_descending_by_lvi(self):
        rows = [
            {"user_id": "low", "total": 10, "correct": 2, "avg_time_ms": 25000, "std_time_ms": 5000},
            {"user_id": "high", "total": 10, "correct": 9, "avg_time_ms": 9000, "std_time_ms": 1000},
        ]
        results = compute_lvi_rows(rows)
        assert results[0]["user_id"] == "high"
        assert results[0]["rank"] == 1
        assert results[1]["rank"] == 2

    def test_empty_input(self):
        assert compute_lvi_rows([]) == []


class TestFatigueAnalysis:
    def test_worked_example_deltas_and_slopes(self):
        raw_buckets = [
            {"bucket_index": 0, "total": 10, "correct": 9, "avg_time_ms": 15000},
            {"bucket_index": 1, "total": 10, "correct": 8, "avg_time_ms": 17000},
            {"bucket_index": 2, "total": 10, "correct": 7, "avg_time_ms": 20000},
            {"bucket_index": 3, "total": 10, "correct": 6, "avg_time_ms": 25000},
        ]
        result = compute_fatigue_buckets(raw_buckets)

        assert result["accuracy_delta"] == pytest.approx(-0.30, abs=1e-9)
        assert result["accuracy_slope"] == pytest.approx(-0.10, abs=1e-9)
        assert result["time_delta"] == pytest.approx(10000.0)
        assert result["time_slope"] == pytest.approx(3300.0, abs=1.0)
        assert result["buckets"][0]["bucket_label"] == "Q1-5"
        assert result["buckets"][1]["bucket_label"] == "Q6-10"

    def test_min_attempts_contributing_filters_trend(self):
        raw_buckets = [
            {"bucket_index": 0, "total": 10, "correct": 9, "avg_time_ms": 15000, "n_attempts_contributing": 10},
            {"bucket_index": 1, "total": 10, "correct": 8, "avg_time_ms": 17000, "n_attempts_contributing": 5},
            # Only one attempt contributes to this late bucket -- should be
            # excluded from the trend regression when threshold is 3.
            {"bucket_index": 2, "total": 2, "correct": 0, "avg_time_ms": 90000, "n_attempts_contributing": 1},
        ]
        result = compute_fatigue_buckets(raw_buckets, min_attempts_contributing=3)
        # trend computed only over buckets 0 and 1
        assert result["accuracy_delta"] == pytest.approx(8 / 10 - 9 / 10)
        assert result["time_delta"] == pytest.approx(17000 - 15000)

    def test_empty_input(self):
        result = compute_fatigue_buckets([])
        assert result["buckets"] == []
        assert result["accuracy_delta"] is None


class TestQuestionDifficultyIndex:
    def test_worked_example(self):
        rows = [
            {
                "_id": "q1",
                "chapter_id": "c1",
                "total": 3,
                "correct": 1,
                "avg_time_ms": 25000,
            }
        ]
        computed = compute_qdi_rows(
            rows,
            global_mean_accuracy=0.65,
            chapter_mean_times={"c1": 18000},
            k=10,
        )
        q1 = computed[0]

        assert q1["shrunk_accuracy"] == pytest.approx(0.5769, abs=1e-3)
        assert q1["shrunk_time_ms"] == pytest.approx(19615.38, abs=0.5)
        # Single question in its chapter cohort -> norm_time = 0.5 (degenerate, only one value)
        # so use a second question to exercise real within-chapter normalization instead:

    def test_within_chapter_time_normalization_and_qdi_value(self):
        rows = [
            {"_id": "q1", "chapter_id": "c1", "total": 3, "correct": 1, "avg_time_ms": 25000},
            {"_id": "q2", "chapter_id": "c1", "total": 20, "correct": 15, "avg_time_ms": 10000},
        ]
        # Craft chapter_mean_time and shrinkage so q1's shrunk_time lands at
        # 19615.38 and q2's raw avg (10000, well-attested at n=20) barely shrinks.
        computed = compute_qdi_rows(rows, global_mean_accuracy=0.65, chapter_mean_times={"c1": 18000}, k=10)
        by_id = {r["question_id"]: r for r in computed}

        q1 = by_id["q1"]
        q2 = by_id["q2"]
        # q2 shrunk_time = (20*10000 + 10*18000)/30 = 12666.67 (min of the two)
        assert q2["shrunk_time_ms"] == pytest.approx(12666.67, abs=1.0)
        # q1 shrunk_time = 19615.38 (max of the two) -> norm_time = 1.0
        assert q1["shrunk_time_ms"] == pytest.approx(19615.38, abs=0.5)

        # QDI = 100*(0.7*(1-0.5769) + 0.3*1.0) = 100*(0.2962+0.3) = 59.62
        assert q1["qdi"] == pytest.approx(59.62, abs=0.5)
        assert q1["confidence"] == "low"  # total_attempts=3 < 5
        assert q2["confidence"] == "high"  # total_attempts=20 >= 20

        # Ranked hardest (highest QDI) first.
        assert computed[0]["question_id"] == "q1"
        assert computed[0]["rank"] == 1

    def test_empty_input(self):
        assert compute_qdi_rows([], 0.5, {}, 10) == []


class TestChapterMastery:
    def test_mastery_formula(self):
        rows = [
            {"user_id": "u1", "chapter_id": "c1", "total": 10, "correct": 8, "avg_time_ms": 12000},
            {"user_id": "u2", "chapter_id": "c1", "total": 10, "correct": 4, "avg_time_ms": 20000},
        ]
        cohort_mean_accuracy = {"c1": 0.6}
        computed = compute_mastery_rows(rows, cohort_mean_accuracy, k=10, prior_key="chapter_id")
        by_user = {r["user_id"]: r for r in computed}

        u1 = by_user["u1"]
        # shrunk_accuracy = (8 + 10*0.6)/20 = 0.70
        assert u1["shrunk_accuracy"] == pytest.approx(0.70)
        # speed_score for u1 (faster, 12000ms) should be higher than u2's (20000ms)
        assert u1["mastery_score"] > by_user["u2"]["mastery_score"]

    def test_uses_precomputed_speed_scores_when_given(self):
        rows = [
            {"user_id": "u1", "chapter_id": "c1", "total": 10, "correct": 8, "avg_time_ms": 12000},
        ]
        computed = compute_mastery_rows(
            rows, {"c1": 0.6}, k=10, prior_key="chapter_id", speed_scores=[1.0]
        )
        # MasteryScore = 100*(0.7*0.70 + 0.3*1.0) = 79.0
        assert computed[0]["mastery_score"] == pytest.approx(79.0, abs=0.1)

    def test_empty_input(self):
        assert compute_mastery_rows([], {}, 10, "chapter_id") == []
