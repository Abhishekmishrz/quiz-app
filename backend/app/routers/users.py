from typing import List

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.repositories import user_repo
from app.schemas.common import PagedResponse
from app.schemas.user import UserOut

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=PagedResponse[UserOut])
async def list_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    docs = await user_repo.list_users(db, limit=limit, offset=offset)
    total = await user_repo.count_users(db)
    items = [UserOut(id=str(d["_id"]), **{k: v for k, v in d.items() if k != "_id"}) for d in docs]
    return PagedResponse[UserOut](items=items, total=total, limit=limit, offset=offset)
