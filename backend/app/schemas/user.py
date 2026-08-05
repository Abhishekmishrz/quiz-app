from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import PyObjectId


class UserOut(BaseModel):
    id: PyObjectId
    name: str
    email: str
    avatar_seed: str
    created_at: datetime


class SessionCreate(BaseModel):
    user_id: str


class SessionOut(BaseModel):
    user_id: str
    name: str
