"""Raw motor queries against `exams`."""
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


async def list_exams(db: AsyncIOMotorDatabase) -> List[Dict[str, Any]]:
    cursor = db.exams.find().sort("name", 1)
    return [doc async for doc in cursor]


async def get_exam_by_id(db: AsyncIOMotorDatabase, exam_id: str) -> Optional[Dict[str, Any]]:
    if not ObjectId.is_valid(exam_id):
        return None
    return await db.exams.find_one({"_id": ObjectId(exam_id)})
