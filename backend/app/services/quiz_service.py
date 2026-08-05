"""Quiz-taking flow: start/resume, current-question, submit-answer, result.

`question_events` is the ONLY source of truth for progress through a quiz.
There is no separately-maintained pointer field (`current_index`) anywhere
that could ever drift out of sync with the events collection -- see the
module docstring in app/models/quiz_attempt.py and app/models/question_event.py
for the crash-consistency rationale.
"""
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.repositories import chapter_repo, question_repo, quiz_repo


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _reorder_options(question_doc: Dict[str, Any], order: list[str]) -> list[Dict[str, str]]:
    """Reorder a question's options per the attempt's persisted option_order."""
    by_key = {opt["key"]: opt["text"] for opt in question_doc["options"]}
    return [{"key": k, "text": by_key[k]} for k in order]


def _to_public_question(
    question_doc: Dict[str, Any], option_order: list[str], question_index: int, total_questions: int
) -> Dict[str, Any]:
    """Strip a question document down to what a quiz-taking client may see:
    NEVER includes correct_option or seed_difficulty."""
    return {
        "id": str(question_doc["_id"]),
        "chapter_id": str(question_doc["chapter_id"]),
        "text": question_doc["text"],
        "options": _reorder_options(question_doc, option_order),
        "question_index": question_index,
        "total_questions": total_questions,
    }


async def _attempt_out(db: AsyncIOMotorDatabase, attempt: Dict[str, Any], resumed: bool = False) -> Dict[str, Any]:
    answered_count = await quiz_repo.count_answered(db, attempt["_id"])
    return {
        "id": str(attempt["_id"]),
        "user_id": str(attempt["user_id"]),
        "exam_id": str(attempt["exam_id"]),
        "subject_id": str(attempt["subject_id"]),
        "chapter_id": str(attempt["chapter_id"]),
        "status": attempt["status"],
        "total_questions": attempt["total_questions"],
        "answered_count": answered_count,
        "started_at": attempt["started_at"],
        "completed_at": attempt.get("completed_at"),
        "resumed": resumed,
    }


async def _ensure_ownership(attempt: Dict[str, Any], current_user_id: str) -> None:
    if str(attempt["user_id"]) != current_user_id:
        raise ForbiddenError("You do not have access to this quiz attempt.", code="forbidden")


async def start_or_resume_attempt(
    db: AsyncIOMotorDatabase, user_id: str, chapter_id: str
) -> Dict[str, Any]:
    if not ObjectId.is_valid(chapter_id):
        raise NotFoundError("Chapter not found.", code="chapter_not_found")

    chapter = await chapter_repo.get_chapter_by_id(db, chapter_id)
    if chapter is None:
        raise NotFoundError("Chapter not found.", code="chapter_not_found")

    user_oid = ObjectId(user_id)
    chapter_oid = ObjectId(chapter_id)

    existing = await quiz_repo.find_in_progress_attempt(db, user_oid, chapter_oid)
    if existing is not None:
        age = _now() - existing["started_at"].replace(tzinfo=timezone.utc)
        if age <= timedelta(minutes=settings.ATTEMPT_FRESHNESS_MINUTES):
            # Resume: return attempt + its current question.
            attempt_out = await _attempt_out(db, existing, resumed=True)
            current_question = await get_current_question(db, str(existing["_id"]), user_id)
            return {"attempt": attempt_out, "current_question": current_question}
        else:
            await quiz_repo.mark_attempt_abandoned(db, existing["_id"])

    # Fresh attempt: sample question ids without replacement.
    all_question_ids = await question_repo.list_question_ids_for_chapter(db, chapter_oid)
    if not all_question_ids:
        raise ValidationAppError("This chapter has no questions yet.", code="empty_chapter")

    quiz_length = min(settings.DEFAULT_QUIZ_LENGTH, len(all_question_ids))
    sampled_ids = random.sample(all_question_ids, quiz_length)

    questions_by_id = await question_repo.get_questions_by_ids(db, sampled_ids)

    option_order: Dict[str, list[str]] = {}
    for qid in sampled_ids:
        keys = [opt["key"] for opt in questions_by_id[str(qid)]["options"]]
        shuffled = keys[:]
        random.shuffle(shuffled)
        option_order[str(qid)] = shuffled

    now = _now()
    attempt_doc = {
        "user_id": user_oid,
        "exam_id": ObjectId(chapter["exam_id"]),
        "subject_id": ObjectId(chapter["subject_id"]),
        "chapter_id": chapter_oid,
        "question_ids": sampled_ids,
        "option_order": option_order,
        "status": "in_progress",
        "total_questions": quiz_length,
        "started_at": now,
        "completed_at": None,
    }
    attempt_id = await quiz_repo.insert_attempt(db, attempt_doc)
    attempt_doc["_id"] = attempt_id

    # Stamp shown_at for the first question right away.
    first_qid = sampled_ids[0]
    await quiz_repo.upsert_shown_event(
        db,
        {
            "quiz_attempt_id": attempt_id,
            "user_id": user_oid,
            "question_id": first_qid,
            "exam_id": attempt_doc["exam_id"],
            "subject_id": attempt_doc["subject_id"],
            "chapter_id": chapter_oid,
            "question_index": 0,
            "shown_at": now,
            "submitted_at": None,
            "response_duration_ms": None,
            "selected_option": None,
            "is_correct": None,
        },
    )

    attempt_out = await _attempt_out(db, attempt_doc, resumed=False)
    first_question_doc = questions_by_id[str(first_qid)]
    current_question = _to_public_question(first_question_doc, option_order[str(first_qid)], 0, quiz_length)
    return {"attempt": attempt_out, "current_question": current_question}


async def get_current_question(db: AsyncIOMotorDatabase, attempt_id: str, current_user_id: str) -> Dict[str, Any]:
    attempt = await quiz_repo.get_attempt_by_id(db, attempt_id)
    if attempt is None:
        raise NotFoundError("Quiz attempt not found.", code="attempt_not_found")
    await _ensure_ownership(attempt, current_user_id)

    answered_count = await quiz_repo.count_answered(db, attempt["_id"])
    total_questions = attempt["total_questions"]
    if answered_count >= total_questions:
        raise ConflictError("This quiz attempt is already complete.", code="attempt_complete")

    question_id = attempt["question_ids"][answered_count]
    question_doc = await question_repo.get_question_by_id(db, question_id)
    if question_doc is None:
        raise NotFoundError("Question not found.", code="question_not_found")

    now = _now()
    await quiz_repo.upsert_shown_event(
        db,
        {
            "quiz_attempt_id": attempt["_id"],
            "user_id": attempt["user_id"],
            "question_id": question_id,
            "exam_id": attempt["exam_id"],
            "subject_id": attempt["subject_id"],
            "chapter_id": attempt["chapter_id"],
            "question_index": answered_count,
            "shown_at": now,
            "submitted_at": None,
            "response_duration_ms": None,
            "selected_option": None,
            "is_correct": None,
        },
    )

    order = attempt["option_order"][str(question_id)]
    return _to_public_question(question_doc, order, answered_count, total_questions)


async def submit_answer(
    db: AsyncIOMotorDatabase,
    attempt_id: str,
    current_user_id: str,
    question_id: str,
    selected_option: str,
) -> Dict[str, Any]:
    attempt = await quiz_repo.get_attempt_by_id(db, attempt_id)
    if attempt is None:
        raise NotFoundError("Quiz attempt not found.", code="attempt_not_found")
    await _ensure_ownership(attempt, current_user_id)

    if not ObjectId.is_valid(question_id):
        raise ValidationAppError("question_id is not a valid id.", code="invalid_question_id")
    question_oid = ObjectId(question_id)

    answered_count = await quiz_repo.count_answered(db, attempt["_id"])
    total_questions = attempt["total_questions"]
    if answered_count >= total_questions:
        raise ConflictError("This quiz attempt is already complete.", code="attempt_complete")

    expected_question_id = attempt["question_ids"][answered_count]
    if question_oid != expected_question_id:
        raise ConflictError(
            "This is not the current question for this attempt (stale, out-of-order, or replayed request).",
            code="question_out_of_order",
        )

    question_doc = await question_repo.get_question_by_id(db, question_oid)
    if question_doc is None:
        raise NotFoundError("Question not found.", code="question_not_found")

    valid_keys = {opt["key"] for opt in question_doc["options"]}
    if not selected_option or selected_option not in valid_keys:
        raise ValidationAppError(
            f"selected_option must be one of {sorted(valid_keys)}.", code="invalid_selected_option"
        )

    event = await quiz_repo.get_event(db, attempt["_id"], question_oid)
    if event is None:
        raise ConflictError("This question has not been shown yet in this attempt.", code="question_not_shown")

    now = _now()
    is_correct = selected_option == question_doc["correct_option"]
    shown_at = event["shown_at"]
    if shown_at.tzinfo is None:
        shown_at = shown_at.replace(tzinfo=timezone.utc)
    duration_ms = (now - shown_at).total_seconds() * 1000

    result = await quiz_repo.guarded_submit_answer(
        db, attempt["_id"], question_oid, now, selected_option, is_correct, duration_ms
    )
    if result.matched_count == 0:
        raise ConflictError("This question has already been answered.", code="already_answered")

    # Best-effort follow-up: not the correctness guard, purely a read cache.
    new_answered_count = await quiz_repo.count_answered(db, attempt["_id"])
    completed = new_answered_count >= total_questions
    if completed:
        await quiz_repo.mark_attempt_completed(db, attempt["_id"], now)

    # Never echo back is_correct here -- correctness only ever revealed via /result.
    return {"advanced": True, "completed": completed}


async def get_result(db: AsyncIOMotorDatabase, attempt_id: str, current_user_id: str) -> Dict[str, Any]:
    attempt = await quiz_repo.get_attempt_by_id(db, attempt_id)
    if attempt is None:
        raise NotFoundError("Quiz attempt not found.", code="attempt_not_found")
    await _ensure_ownership(attempt, current_user_id)

    total_questions = attempt["total_questions"]
    answered_count = await quiz_repo.count_answered(db, attempt["_id"])
    if answered_count < total_questions:
        raise ConflictError("This quiz attempt is not yet complete.", code="attempt_incomplete")

    agg = await quiz_repo.aggregate_attempt_result(db, attempt["_id"])
    correct_count = agg.get("correct_count", 0)
    agg_total = agg.get("total_questions", 0) or total_questions
    score_percent = (correct_count / agg_total * 100) if agg_total else 0.0

    events = await quiz_repo.list_events_for_attempt(db, attempt["_id"])
    events_by_qid = {str(e["question_id"]): e for e in events}
    questions_by_id = await question_repo.get_questions_by_ids(db, attempt["question_ids"])

    review = []
    for qid in attempt["question_ids"]:
        q_doc = questions_by_id[str(qid)]
        event = events_by_qid.get(str(qid), {})
        order = attempt["option_order"].get(str(qid), [opt["key"] for opt in q_doc["options"]])
        review.append(
            {
                "id": str(q_doc["_id"]),
                "text": q_doc["text"],
                "options": _reorder_options(q_doc, order),
                "correct_option": q_doc["correct_option"],
                "selected_option": event.get("selected_option"),
                "is_correct": event.get("is_correct"),
            }
        )

    return {
        "attempt_id": str(attempt["_id"]),
        "correct_count": correct_count,
        "total_questions": agg_total,
        "score_percent": score_percent,
        "review": review,
    }
