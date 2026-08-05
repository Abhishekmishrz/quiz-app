"""Internal Mongo document shape for `questions`.

Includes ALL fields, including `correct_option` and `seed_difficulty` --
these are the fields the API-facing schema must never serialize back to a
quiz-taking client (see app/schemas/question.py).
"""
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PyObjectId


class OptionDoc(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    key: str  # "A" | "B" | "C" | "D"
    text: str


class QuestionDoc(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    chapter_id: PyObjectId
    subject_id: PyObjectId  # denormalized
    exam_id: PyObjectId  # denormalized
    text: str
    options: List[OptionDoc]
    correct_option: str
    seed_difficulty: float  # hidden, seed-only, never serialized to clients
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
