"""Internal Mongo document shape for `users`."""
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PyObjectId


class UserDoc(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    name: str
    email: str
    avatar_seed: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
