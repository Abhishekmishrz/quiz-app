"""Raw motor queries against `users`. No business rules here."""
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


async def list_users(db: AsyncIOMotorDatabase, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    cursor = db.users.find().sort("name", 1).skip(offset).limit(limit)
    return [doc async for doc in cursor]


async def count_users(db: AsyncIOMotorDatabase) -> int:
    return await db.users.count_documents({})


async def get_user_by_id(db: AsyncIOMotorDatabase, user_id: str) -> Optional[Dict[str, Any]]:
    if not ObjectId.is_valid(user_id):
        return None
    return await db.users.find_one({"_id": ObjectId(user_id)})


async def get_users_by_ids(db: AsyncIOMotorDatabase, user_ids: List[ObjectId]) -> Dict[str, Dict[str, Any]]:
    cursor = db.users.find({"_id": {"$in": user_ids}})
    result: Dict[str, Dict[str, Any]] = {}
    async for doc in cursor:
        result[str(doc["_id"])] = doc
    return result
