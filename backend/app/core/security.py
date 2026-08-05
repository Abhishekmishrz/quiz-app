"""Dummy authentication: identity is carried in the X-User-Id header.

No passwords or tokens -- the brief explicitly allows dummy auth. Ownership
checks on attempt-scoped endpoints are still enforced server-side despite
the auth itself being dummy (see services/quiz_service.py).
"""
from bson import ObjectId
from fastapi import Depends, Header
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.errors import UnauthorizedError


async def get_current_user_id(
    x_user_id: str = Header(..., alias="X-User-Id"),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> str:
    """Validate the X-User-Id header references a real, existing user.

    Raises 401 if the header is missing (FastAPI handles that via Header(...))
    or the value isn't a valid/known user id.

    Goes through the same `get_db` FastAPI dependency every router uses
    (rather than reaching for the module-scope client directly) so that
    dependency_overrides in tests correctly redirect this check too.
    """
    if not x_user_id or not ObjectId.is_valid(x_user_id):
        raise UnauthorizedError("X-User-Id header missing or not a valid user id.", code="unauthorized")

    user = await db.users.find_one({"_id": ObjectId(x_user_id)}, {"_id": 1})
    if user is None:
        raise UnauthorizedError("X-User-Id does not reference a known user.", code="unauthorized")

    return x_user_id
