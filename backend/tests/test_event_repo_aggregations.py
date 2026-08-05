"""Aggregation-pipeline tests against a REAL MongoDB (not mocked).

Seeds a handful of hand-crafted question_events into a throwaway test
database and asserts the actual `$group`/`$stdDevPop`/`$floor` pipeline
output in app/repositories/event_repo.py matches hand-computed numbers --
pure-Python unit tests alone would never catch a wrong `$group` stage or an
off-by-one in the bucketing expression.

Skipped automatically (via the `mongo_test_db` fixture) if no MongoDB is
reachable.
"""
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from app.repositories import event_repo

pytestmark = pytest.mark.asyncio


@pytest.fixture
def fixture_ids():
    return {
        "user_a": ObjectId(),
        "user_b": ObjectId(),
        "q1": ObjectId(),
        "q2": ObjectId(),
        "q3": ObjectId(),
        "c1": ObjectId(),
        "c2": ObjectId(),
        "s1": ObjectId(),
        "e1": ObjectId(),
        "t1": ObjectId(),
        "t2": ObjectId(),
    }


def _event(ids, **overrides):
    now = datetime.now(timezone.utc)
    base = {
        "_id": ObjectId(),
        "quiz_attempt_id": ids["t1"],
        "user_id": ids["user_a"],
        "question_id": ids["q1"],
        "exam_id": ids["e1"],
        "subject_id": ids["s1"],
        "chapter_id": ids["c1"],
        "question_index": 0,
        "shown_at": now,
        "submitted_at": now + timedelta(seconds=10),
        "response_duration_ms": 10000,
        "selected_option": "A",
        "is_correct": True,
    }
    base.update(overrides)
    return base


async def _seed(db, ids):
    events = [
        # user A, quiz T1: Q1 correct (10000ms), Q2 incorrect (20000ms)
        _event(ids, question_id=ids["q1"], question_index=0, is_correct=True, response_duration_ms=10000.0),
        _event(
            ids,
            question_id=ids["q2"],
            question_index=1,
            is_correct=False,
            response_duration_ms=20000.0,
        ),
        # user B, quiz T2: Q1 incorrect (14000ms, same chapter C1), Q3 correct (5000ms, chapter C2)
        _event(
            ids,
            quiz_attempt_id=ids["t2"],
            user_id=ids["user_b"],
            question_id=ids["q1"],
            question_index=0,
            is_correct=False,
            response_duration_ms=14000.0,
        ),
        _event(
            ids,
            quiz_attempt_id=ids["t2"],
            user_id=ids["user_b"],
            question_id=ids["q3"],
            chapter_id=ids["c2"],
            question_index=1,
            is_correct=True,
            response_duration_ms=5000.0,
        ),
    ]
    await db.question_events.insert_many(events)


class TestPerUserStats:
    async def test_matches_hand_computed_mean_and_stddev(self, mongo_test_db, fixture_ids):
        await _seed(mongo_test_db, fixture_ids)
        rows = await event_repo.per_user_stats(mongo_test_db)
        by_user = {str(r["_id"]): r for r in rows}

        user_a = by_user[str(fixture_ids["user_a"])]
        assert user_a["total"] == 2
        assert user_a["correct"] == 1
        assert user_a["avg_time_ms"] == pytest.approx(15000.0)
        # population stddev of [10000, 20000] = 5000
        assert user_a["std_time_ms"] == pytest.approx(5000.0)

        user_b = by_user[str(fixture_ids["user_b"])]
        assert user_b["total"] == 2
        assert user_b["correct"] == 1
        assert user_b["avg_time_ms"] == pytest.approx(9500.0)


class TestGlobalAccuracyStats:
    async def test_matches_hand_computed_global_mean(self, mongo_test_db, fixture_ids):
        await _seed(mongo_test_db, fixture_ids)
        stats = await event_repo.global_accuracy_stats(mongo_test_db)
        # 4 total events, 2 correct (A's Q1, B's Q3) -> mean accuracy 0.5
        assert stats["total"] == 4
        assert stats["correct"] == 2
        assert stats["mean_accuracy"] == pytest.approx(0.5)


class TestPerQuestionStats:
    async def test_matches_hand_computed_per_question_rows(self, mongo_test_db, fixture_ids):
        await _seed(mongo_test_db, fixture_ids)
        rows = await event_repo.per_question_stats(mongo_test_db)
        by_qid = {str(r["_id"]): r for r in rows}

        q1 = by_qid[str(fixture_ids["q1"])]
        assert q1["total"] == 2
        assert q1["correct"] == 1
        assert q1["avg_time_ms"] == pytest.approx(12000.0)  # (10000+14000)/2
        assert str(q1["chapter_id"]) == str(fixture_ids["c1"])

        q3 = by_qid[str(fixture_ids["q3"])]
        assert q3["total"] == 1
        assert q3["correct"] == 1
        assert q3["avg_time_ms"] == pytest.approx(5000.0)

    async def test_chapter_filter(self, mongo_test_db, fixture_ids):
        await _seed(mongo_test_db, fixture_ids)
        rows = await event_repo.per_question_stats(mongo_test_db, chapter_id=fixture_ids["c2"])
        assert len(rows) == 1
        assert str(rows[0]["_id"]) == str(fixture_ids["q3"])


class TestChapterMeanTimes:
    async def test_matches_hand_computed_chapter_means(self, mongo_test_db, fixture_ids):
        await _seed(mongo_test_db, fixture_ids)
        means = await event_repo.chapter_mean_times(mongo_test_db)
        # C1 events: 10000, 20000, 14000 -> mean 14666.67
        assert means[str(fixture_ids["c1"])] == pytest.approx(14666.67, abs=0.5)
        # C2 events: 5000
        assert means[str(fixture_ids["c2"])] == pytest.approx(5000.0)


class TestFatigueSingleAttempt:
    async def test_bucketing_and_stats(self, mongo_test_db, fixture_ids):
        await _seed(mongo_test_db, fixture_ids)
        rows = await event_repo.fatigue_single_attempt(mongo_test_db, fixture_ids["t1"])
        # Both of T1's events are question_index 0 and 1 -> bucket 0 (floor(idx/5))
        assert len(rows) == 1
        assert int(rows[0]["_id"]) == 0
        assert rows[0]["total"] == 2
        assert rows[0]["correct"] == 1
        assert rows[0]["avg_time_ms"] == pytest.approx(15000.0)


class TestFatigueUserAcrossAttempts:
    async def test_n_attempts_contributing(self, mongo_test_db, fixture_ids):
        await _seed(mongo_test_db, fixture_ids)
        rows = await event_repo.fatigue_user_across_attempts(mongo_test_db, fixture_ids["user_a"])
        assert len(rows) == 1
        assert rows[0]["n_attempts_contributing"] == 1  # only quiz T1 contributes for user A


class TestUserChapterStats:
    async def test_matches_hand_computed(self, mongo_test_db, fixture_ids):
        await _seed(mongo_test_db, fixture_ids)
        rows = await event_repo.user_chapter_stats(mongo_test_db, user_id=fixture_ids["user_a"])
        assert len(rows) == 1
        row = rows[0]
        assert str(row["chapter_id"]) == str(fixture_ids["c1"])
        assert row["total"] == 2
        assert row["correct"] == 1
        assert row["avg_time_ms"] == pytest.approx(15000.0)


class TestChapterCohortAccuracy:
    async def test_matches_hand_computed(self, mongo_test_db, fixture_ids):
        await _seed(mongo_test_db, fixture_ids)
        result = await event_repo.chapter_cohort_accuracy(mongo_test_db, [fixture_ids["c1"]])
        # C1 events: A's Q1 (correct), A's Q2 (incorrect), B's Q1 (incorrect) -> 1/3
        assert result[str(fixture_ids["c1"])] == pytest.approx(1 / 3, abs=1e-6)
