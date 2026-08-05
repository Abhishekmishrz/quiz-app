"""Raw motor queries against `quiz_attempts` and `question_events`.

No business rules here -- resume/expiry/ordering logic lives in
services/quiz_service.py. This module only knows how to read/write documents.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


# ---- quiz_attempts ----

async def find_in_progress_attempt(
    db: AsyncIOMotorDatabase, user_id: ObjectId, chapter_id: ObjectId
) -> Optional[Dict[str, Any]]:
    return await db.quiz_attempts.find_one(
        {"user_id": user_id, "chapter_id": chapter_id, "status": "in_progress"},
        sort=[("started_at", -1)],
    )


async def mark_attempt_abandoned(db: AsyncIOMotorDatabase, attempt_id: ObjectId) -> None:
    await db.quiz_attempts.update_one({"_id": attempt_id}, {"$set": {"status": "abandoned"}})


async def insert_attempt(db: AsyncIOMotorDatabase, doc: Dict[str, Any]) -> ObjectId:
    result = await db.quiz_attempts.insert_one(doc)
    return result.inserted_id


async def get_attempt_by_id(db: AsyncIOMotorDatabase, attempt_id: str) -> Optional[Dict[str, Any]]:
    if not ObjectId.is_valid(attempt_id):
        return None
    return await db.quiz_attempts.find_one({"_id": ObjectId(attempt_id)})


async def mark_attempt_completed(db: AsyncIOMotorDatabase, attempt_id: ObjectId, completed_at: datetime) -> None:
    """Best-effort cache update -- correctness never depends on this
    succeeding; /result recomputes from question_events regardless."""
    await db.quiz_attempts.update_one(
        {"_id": attempt_id},
        {"$set": {"status": "completed", "completed_at": completed_at}},
    )


# ---- question_events ----

async def upsert_shown_event(db: AsyncIOMotorDatabase, event_doc: Dict[str, Any]) -> None:
    """Idempotent upsert: only sets shown_at (and the rest of the doc) on
    first insert, so a page refresh never resets the clock."""
    await db.question_events.update_one(
        {"quiz_attempt_id": event_doc["quiz_attempt_id"], "question_id": event_doc["question_id"]},
        {"$setOnInsert": event_doc},
        upsert=True,
    )


async def get_event(db: AsyncIOMotorDatabase, attempt_id: ObjectId, question_id: ObjectId) -> Optional[Dict[str, Any]]:
    return await db.question_events.find_one({"quiz_attempt_id": attempt_id, "question_id": question_id})


async def count_answered(db: AsyncIOMotorDatabase, attempt_id: ObjectId) -> int:
    return await db.question_events.count_documents(
        {"quiz_attempt_id": attempt_id, "submitted_at": {"$ne": None}}
    )


async def guarded_submit_answer(
    db: AsyncIOMotorDatabase,
    attempt_id: ObjectId,
    question_id: ObjectId,
    now: datetime,
    selected_option: str,
    is_correct: bool,
    duration_ms: float,
):
    """The entire concurrency guard: matches only if submitted_at is still
    None. Of two simultaneous submissions, exactly one matches."""
    return await db.question_events.update_one(
        {"quiz_attempt_id": attempt_id, "question_id": question_id, "submitted_at": None},
        {
            "$set": {
                "submitted_at": now,
                "selected_option": selected_option,
                "is_correct": is_correct,
                "response_duration_ms": duration_ms,
            }
        },
    )


async def list_events_for_attempt(db: AsyncIOMotorDatabase, attempt_id: ObjectId) -> List[Dict[str, Any]]:
    cursor = db.question_events.find({"quiz_attempt_id": attempt_id}).sort("question_index", 1)
    return [doc async for doc in cursor]


async def aggregate_attempt_result(db: AsyncIOMotorDatabase, attempt_id: ObjectId) -> Dict[str, Any]:
    """$group over this attempt's answered events -> correct_count/total."""
    pipeline = [
        {"$match": {"quiz_attempt_id": attempt_id, "submitted_at": {"$ne": None}}},
        {
            "$group": {
                "_id": None,
                "total_questions": {"$sum": 1},
                "correct_count": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
            }
        },
    ]
    result = [doc async for doc in db.question_events.aggregate(pipeline)]
    if not result:
        return {"total_questions": 0, "correct_count": 0}
    return result[0]
