"""Internal Mongo document shape for `subjects`."""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PyObjectId


class SubjectDoc(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    exam_id: PyObjectId
    name: str
    code: str
    order: int
