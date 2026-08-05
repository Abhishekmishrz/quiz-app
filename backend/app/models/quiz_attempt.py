"""Internal Mongo document shape for `quiz_attempts`.

Deliberately NO `current_index`/`correct_count`/`score_percent` fields --
these are always derived on read from `question_events`, the single source
of truth for progress through a quiz (see services/quiz_service.py).
"""
from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PyObjectId

AttemptStatus = Literal["in_progress", "completed", "abandoned"]


class QuizAttemptDoc(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: PyObjectId
    exam_id: PyObjectId
    subject_id: PyObjectId
    chapter_id: PyObjectId
    question_ids: List[PyObjectId]  # fixed order decided at creation
    option_order: Dict[str, List[str]]  # question_id_str -> ["A","C","B","D"]
    status: AttemptStatus = "in_progress"  # best-effort cache, not source of truth
    total_questions: int
    started_at: datetime
    completed_at: Optional[datetime] = None
