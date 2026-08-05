"""Internal Mongo document shape for `question_events` -- the analytics
fact table. Every analytic depends on this shape.

`question_events` is the ONLY source of truth for progress through a quiz.
There is no separately-maintained pointer field on `quiz_attempts` that
could ever drift out of sync with this collection.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PyObjectId


class QuestionEventDoc(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    quiz_attempt_id: PyObjectId
    user_id: PyObjectId
    question_id: PyObjectId
    exam_id: PyObjectId  # denormalized
    subject_id: PyObjectId  # denormalized
    chapter_id: PyObjectId  # denormalized
    question_index: int  # 0-based position within the attempt
    shown_at: datetime
    submitted_at: Optional[datetime] = None
    response_duration_ms: Optional[float] = None
    selected_option: Optional[str] = None
    is_correct: Optional[bool] = None
