"""Internal Mongo document shape for `chapters`."""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PyObjectId


class ChapterDoc(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    subject_id: PyObjectId
    exam_id: PyObjectId  # denormalized
    name: str
    order: int
