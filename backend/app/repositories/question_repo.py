"""Raw motor queries against `questions`."""
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


async def get_question_by_id(db: AsyncIOMotorDatabase, question_id) -> Optional[Dict[str, Any]]:
    oid = question_id if isinstance(question_id, ObjectId) else ObjectId(question_id)
    return await db.questions.find_one({"_id": oid})


async def get_questions_by_ids(db: AsyncIOMotorDatabase, question_ids: List[ObjectId]) -> Dict[str, Dict[str, Any]]:
    cursor = db.questions.find({"_id": {"$in": question_ids}})
    result: Dict[str, Dict[str, Any]] = {}
    async for doc in cursor:
        result[str(doc["_id"])] = doc
    return result


async def list_question_ids_for_chapter(db: AsyncIOMotorDatabase, chapter_id: ObjectId) -> List[ObjectId]:
    cursor = db.questions.find({"chapter_id": chapter_id}, {"_id": 1})
    return [doc["_id"] async for doc in cursor]


async def count_questions_for_chapter(db: AsyncIOMotorDatabase, chapter_id: ObjectId) -> int:
    return await db.questions.count_documents({"chapter_id": chapter_id})
