from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.errors import NotFoundError
from app.repositories import user_repo
from app.schemas.user import SessionCreate, SessionOut

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut)
async def create_session(payload: SessionCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Dummy login: validates the user exists and returns {user_id, name}.
    No real token -- the client just stores this and sends X-User-Id on
    subsequent requests."""
    user = await user_repo.get_user_by_id(db, payload.user_id)
    if user is None:
        raise NotFoundError("User not found.", code="user_not_found")
    return SessionOut(user_id=str(user["_id"]), name=user["name"])
