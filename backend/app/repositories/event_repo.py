"""Raw aggregation pipelines over `question_events` -- the fact table behind
all four analytics endpoints.

This module does ONLY the per-entity Mongo `$group`/`$avg`/`$stdDevPop`
work (scales with event volume, stays indexed). The small cross-sectional
step -- normalization across ~50 users or ~500 questions, Bayesian
shrinkage, regression slopes -- is plain Python/numpy and lives in
services/analytics_service.py. No business rules or formulas belong here.
"""
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

ANSWERED_MATCH = {"submitted_at": {"$ne": None}}


# ---------------------------------------------------------------------------
# Learning Velocity Index
# ---------------------------------------------------------------------------

async def per_user_stats(db: AsyncIOMotorDatabase) -> List[Dict[str, Any]]:
    """Per-user accuracy/time stats across ALL of that user's answered
    events, for the Learning Velocity Index."""
    pipeline = [
        {"$match": ANSWERED_MATCH},
        {
            "$group": {
                "_id": "$user_id",
                "total": {"$sum": 1},
                "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
                "avg_time_ms": {"$avg": "$response_duration_ms"},
                "std_time_ms": {"$stdDevPop": "$response_duration_ms"},
            }
        },
    ]
    return [doc async for doc in db.question_events.aggregate(pipeline)]


# ---------------------------------------------------------------------------
# Fatigue analysis
# ---------------------------------------------------------------------------

_BUCKET_STAGE = {"$addFields": {"bucket_index": {"$floor": {"$divide": ["$question_index", 5]}}}}


async def fatigue_single_attempt(db: AsyncIOMotorDatabase, attempt_id: ObjectId) -> List[Dict[str, Any]]:
    """Bucketed accuracy/time for a single quiz attempt."""
    pipeline = [
        {"$match": {"quiz_attempt_id": attempt_id, **ANSWERED_MATCH}},
        _BUCKET_STAGE,
        {
            "$group": {
                "_id": "$bucket_index",
                "total": {"$sum": 1},
                "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
                "avg_time_ms": {"$avg": "$response_duration_ms"},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    return [doc async for doc in db.question_events.aggregate(pipeline)]


async def fatigue_user_across_attempts(db: AsyncIOMotorDatabase, user_id: ObjectId) -> List[Dict[str, Any]]:
    """Bucketed accuracy/time for a user across all of their attempts, plus
    n_attempts_contributing (distinct quiz_attempt_id count) per bucket."""
    pipeline = [
        {"$match": {"user_id": user_id, **ANSWERED_MATCH}},
        _BUCKET_STAGE,
        {
            "$group": {
                "_id": "$bucket_index",
                "total": {"$sum": 1},
                "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
                "avg_time_ms": {"$avg": "$response_duration_ms"},
                "attempt_ids": {"$addToSet": "$quiz_attempt_id"},
            }
        },
        {"$addFields": {"n_attempts_contributing": {"$size": "$attempt_ids"}}},
        {"$project": {"attempt_ids": 0}},
        {"$sort": {"_id": 1}},
    ]
    return [doc async for doc in db.question_events.aggregate(pipeline)]


# ---------------------------------------------------------------------------
# Question Difficulty Index
# ---------------------------------------------------------------------------

async def global_accuracy_stats(db: AsyncIOMotorDatabase) -> Dict[str, Any]:
    """Global mean accuracy over ALL answered events (unfiltered) -- the
    shrinkage prior for QDI's accuracy term."""
    pipeline = [
        {"$match": ANSWERED_MATCH},
        {
            "$group": {
                "_id": None,
                "total": {"$sum": 1},
                "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
            }
        },
    ]
    result = [doc async for doc in db.question_events.aggregate(pipeline)]
    if not result or result[0]["total"] == 0:
        return {"total": 0, "correct": 0, "mean_accuracy": 0.5}
    total, correct = result[0]["total"], result[0]["correct"]
    return {"total": total, "correct": correct, "mean_accuracy": correct / total}


async def per_question_stats(
    db: AsyncIOMotorDatabase,
    exam_id: Optional[ObjectId] = None,
    subject_id: Optional[ObjectId] = None,
    chapter_id: Optional[ObjectId] = None,
) -> List[Dict[str, Any]]:
    """Per-question raw stats, optionally filtered by exam/subject/chapter."""
    match: Dict[str, Any] = dict(ANSWERED_MATCH)
    if exam_id is not None:
        match["exam_id"] = exam_id
    if subject_id is not None:
        match["subject_id"] = subject_id
    if chapter_id is not None:
        match["chapter_id"] = chapter_id

    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": "$question_id",
                "chapter_id": {"$first": "$chapter_id"},
                "subject_id": {"$first": "$subject_id"},
                "exam_id": {"$first": "$exam_id"},
                "total": {"$sum": 1},
                "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
                "avg_time_ms": {"$avg": "$response_duration_ms"},
            }
        },
    ]
    return [doc async for doc in db.question_events.aggregate(pipeline)]


async def chapter_mean_times(db: AsyncIOMotorDatabase) -> Dict[str, float]:
    """Mean response time per chapter, over ALL answered events for that
    chapter -- the shrinkage prior for QDI's (and Mastery's) time term."""
    pipeline = [
        {"$match": ANSWERED_MATCH},
        {"$group": {"_id": "$chapter_id", "mean_time_ms": {"$avg": "$response_duration_ms"}}},
    ]
    result = [doc async for doc in db.question_events.aggregate(pipeline)]
    return {str(doc["_id"]): doc["mean_time_ms"] for doc in result}


# ---------------------------------------------------------------------------
# Chapter / Subject Mastery
# ---------------------------------------------------------------------------

async def user_chapter_stats(
    db: AsyncIOMotorDatabase,
    user_id: Optional[ObjectId] = None,
    chapter_id: Optional[ObjectId] = None,
) -> List[Dict[str, Any]]:
    """Per (user_id, chapter_id) pair stats. Exactly one of user_id/chapter_id
    should be provided by the caller to select personal-vs-cohort mode, but
    this function itself is agnostic -- it just applies whatever filter it's
    given and groups by the other dimension."""
    match: Dict[str, Any] = dict(ANSWERED_MATCH)
    if user_id is not None:
        match["user_id"] = user_id
    if chapter_id is not None:
        match["chapter_id"] = chapter_id

    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": {"user_id": "$user_id", "chapter_id": "$chapter_id"},
                "subject_id": {"$first": "$subject_id"},
                "total": {"$sum": 1},
                "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
                "avg_time_ms": {"$avg": "$response_duration_ms"},
            }
        },
    ]
    result = [doc async for doc in db.question_events.aggregate(pipeline)]
    for doc in result:
        doc["user_id"] = doc["_id"]["user_id"]
        doc["chapter_id"] = doc["_id"]["chapter_id"]
    return result


async def chapter_cohort_pairs(db: AsyncIOMotorDatabase, chapter_ids: List[ObjectId]) -> List[Dict[str, Any]]:
    """Per (user_id, chapter_id) stats for ALL users across the given
    chapters -- used to normalize a single user's speed_score_uc within
    each chapter's own cohort (not across the user's other chapters)."""
    pipeline = [
        {"$match": {"chapter_id": {"$in": chapter_ids}, **ANSWERED_MATCH}},
        {
            "$group": {
                "_id": {"user_id": "$user_id", "chapter_id": "$chapter_id"},
                "total": {"$sum": 1},
                "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
                "avg_time_ms": {"$avg": "$response_duration_ms"},
            }
        },
    ]
    result = [doc async for doc in db.question_events.aggregate(pipeline)]
    for doc in result:
        doc["user_id"] = doc["_id"]["user_id"]
        doc["chapter_id"] = doc["_id"]["chapter_id"]
    return result


async def chapter_cohort_accuracy(db: AsyncIOMotorDatabase, chapter_ids: List[ObjectId]) -> Dict[str, float]:
    """Cohort-wide mean accuracy per chapter (across all users) -- the
    shrinkage prior for Mastery's accuracy term."""
    pipeline = [
        {"$match": {"chapter_id": {"$in": chapter_ids}, **ANSWERED_MATCH}},
        {
            "$group": {
                "_id": "$chapter_id",
                "total": {"$sum": 1},
                "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
            }
        },
    ]
    result = [doc async for doc in db.question_events.aggregate(pipeline)]
    return {str(doc["_id"]): (doc["correct"] / doc["total"] if doc["total"] else 0.5) for doc in result}
