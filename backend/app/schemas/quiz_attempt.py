from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.common import PyObjectId
from app.schemas.question import QuestionPublicOut, QuestionReviewOut


class QuizAttemptCreate(BaseModel):
    chapter_id: str


class QuizAttemptOut(BaseModel):
    id: PyObjectId
    user_id: PyObjectId
    exam_id: PyObjectId
    subject_id: PyObjectId
    chapter_id: PyObjectId
    status: str
    total_questions: int
    answered_count: int
    started_at: datetime
    completed_at: Optional[datetime]
    resumed: bool = False


class QuizAttemptStartOut(BaseModel):
    attempt: QuizAttemptOut
    current_question: QuestionPublicOut


class AnswerSubmit(BaseModel):
    question_id: str
    selected_option: str


class AnswerResultOut(BaseModel):
    advanced: bool
    completed: bool


class QuizResultOut(BaseModel):
    attempt_id: PyObjectId
    correct_count: int
    total_questions: int
    score_percent: float
    review: List[QuestionReviewOut]
