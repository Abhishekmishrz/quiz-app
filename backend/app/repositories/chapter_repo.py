"""Raw motor queries against `chapters`."""
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


async def list_chapters_for_subject(db: AsyncIOMotorDatabase, subject_id: str) -> List[Dict[str, Any]]:
    cursor = db.chapters.find({"subject_id": ObjectId(subject_id)}).sort("order", 1)
    return [doc async for doc in cursor]


async def get_chapter_by_id(db: AsyncIOMotorDatabase, chapter_id: str) -> Optional[Dict[str, Any]]:
    if not ObjectId.is_valid(chapter_id):
        return None
    return await db.chapters.find_one({"_id": ObjectId(chapter_id)})


async def get_chapters_by_ids(db: AsyncIOMotorDatabase, chapter_ids: List[ObjectId]) -> Dict[str, Dict[str, Any]]:
    cursor = db.chapters.find({"_id": {"$in": chapter_ids}})
    result: Dict[str, Dict[str, Any]] = {}
    async for doc in cursor:
        result[str(doc["_id"])] = doc
    return result
