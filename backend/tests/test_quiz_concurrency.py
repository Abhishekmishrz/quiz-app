"""Concurrency test: fires two simultaneous POST .../answers requests for
the same attempt/question and asserts exactly one succeeds and the other
gets a 409 -- proves the guarded `submitted_at: None` update actually
prevents double-recording, not just in theory.

Spins up the real FastAPI app via httpx.AsyncClient(ASGITransport), with
`get_db` overridden to point at a throwaway real-Mongo test database
(skipped automatically if no Mongo is reachable).
"""
import asyncio
from datetime import datetime, timezone

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app

pytestmark = pytest.mark.asyncio


async def _seed_attempt(db):
    now = datetime.now(timezone.utc)

    user_id = ObjectId()
    exam_id = ObjectId()
    subject_id = ObjectId()
    chapter_id = ObjectId()
    question_id = ObjectId()
    attempt_id = ObjectId()

    await db.users.insert_one(
        {"_id": user_id, "name": "Test User", "email": "test@example.com", "avatar_seed": "seed", "created_at": now}
    )
    await db.questions.insert_one(
        {
            "_id": question_id,
            "chapter_id": chapter_id,
            "subject_id": subject_id,
            "exam_id": exam_id,
            "text": "What is 2+2?",
            "options": [
                {"key": "A", "text": "3"},
                {"key": "B", "text": "4"},
                {"key": "C", "text": "5"},
                {"key": "D", "text": "6"},
            ],
            "correct_option": "B",
            "seed_difficulty": 0.3,
            "created_at": now,
        }
    )
    await db.quiz_attempts.insert_one(
        {
            "_id": attempt_id,
            "user_id": user_id,
            "exam_id": exam_id,
            "subject_id": subject_id,
            "chapter_id": chapter_id,
            "question_ids": [question_id],
            "option_order": {str(question_id): ["A", "B", "C", "D"]},
            "status": "in_progress",
            "total_questions": 1,
            "started_at": now,
            "completed_at": None,
        }
    )
    # Simulate current-question already having been fetched: shown_at stamped,
    # not yet answered.
    await db.question_events.insert_one(
        {
            "_id": ObjectId(),
            "quiz_attempt_id": attempt_id,
            "user_id": user_id,
            "question_id": question_id,
            "exam_id": exam_id,
            "subject_id": subject_id,
            "chapter_id": chapter_id,
            "question_index": 0,
            "shown_at": now,
            "submitted_at": None,
            "response_duration_ms": None,
            "selected_option": None,
            "is_correct": None,
        }
    )
    return user_id, attempt_id, question_id


async def test_concurrent_answers_exactly_one_succeeds(mongo_test_db):
    app.dependency_overrides[get_db] = lambda: mongo_test_db
    try:
        user_id, attempt_id, question_id = await _seed_attempt(mongo_test_db)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"X-User-Id": str(user_id)}
            payload = {"question_id": str(question_id), "selected_option": "B"}

            responses = await asyncio.gather(
                client.post(f"/api/v1/quiz-attempts/{attempt_id}/answers", json=payload, headers=headers),
                client.post(f"/api/v1/quiz-attempts/{attempt_id}/answers", json=payload, headers=headers),
            )

        status_codes = sorted(r.status_code for r in responses)
        assert status_codes == [200, 409], f"Expected exactly one 200 and one 409, got {status_codes}"

        succeeded = [r for r in responses if r.status_code == 200][0]
        body = succeeded.json()
        assert body["advanced"] is True
        assert body["completed"] is True  # only question in a 1-question attempt

        conflicted = [r for r in responses if r.status_code == 409][0]
        assert conflicted.json()["code"] == "already_answered"

        # Exactly one event actually recorded as answered -- no double-write.
        answered_count = await mongo_test_db.question_events.count_documents(
            {"quiz_attempt_id": attempt_id, "submitted_at": {"$ne": None}}
        )
        assert answered_count == 1
    finally:
        app.dependency_overrides.pop(get_db, None)


async def test_result_recomputes_from_events_even_if_status_cache_is_stale(mongo_test_db):
    """Proves the `quiz_attempts.status` cache is non-load-bearing: even if
    the best-effort status/completed_at update never happened (simulating a
    crash right after the guarded event write), /result must still compute
    the correct score by recomputing answered_count from question_events."""
    app.dependency_overrides[get_db] = lambda: mongo_test_db
    try:
        user_id, attempt_id, question_id = await _seed_attempt(mongo_test_db)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"X-User-Id": str(user_id)}
            payload = {"question_id": str(question_id), "selected_option": "B"}
            answer_resp = await client.post(
                f"/api/v1/quiz-attempts/{attempt_id}/answers", json=payload, headers=headers
            )
            assert answer_resp.status_code == 200

            # Simulate the crash: force status back to in_progress, as if the
            # best-effort follow-up write was lost.
            await mongo_test_db.quiz_attempts.update_one(
                {"_id": attempt_id}, {"$set": {"status": "in_progress", "completed_at": None}}
            )

            result_resp = await client.get(f"/api/v1/quiz-attempts/{attempt_id}/result", headers=headers)

        assert result_resp.status_code == 200
        body = result_resp.json()
        assert body["correct_count"] == 1
        assert body["total_questions"] == 1
        assert body["score_percent"] == pytest.approx(100.0)
    finally:
        app.dependency_overrides.pop(get_db, None)
