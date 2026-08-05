"""Raw motor queries against `subjects`."""
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


async def list_subjects_for_exam(db: AsyncIOMotorDatabase, exam_id: str) -> List[Dict[str, Any]]:
    cursor = db.subjects.find({"exam_id": ObjectId(exam_id)}).sort("order", 1)
    return [doc async for doc in cursor]


async def get_subject_by_id(db: AsyncIOMotorDatabase, subject_id: str) -> Optional[Dict[str, Any]]:
    if not ObjectId.is_valid(subject_id):
        return None
    return await db.subjects.find_one({"_id": ObjectId(subject_id)})


async def get_subjects_by_ids(db: AsyncIOMotorDatabase, subject_ids: List[ObjectId]) -> Dict[str, Dict[str, Any]]:
    cursor = db.subjects.find({"_id": {"$in": subject_ids}})
    result: Dict[str, Dict[str, Any]] = {}
    async for doc in cursor:
        result[str(doc["_id"])] = doc
    return result
