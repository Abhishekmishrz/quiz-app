"""API-facing question schemas.

CRITICAL: these response schemas OMIT `correct_option` and `seed_difficulty`
entirely -- they must never be serialized to a quiz-taking client. Only the
review schema used in the post-completion /result payload exposes
`correct_option`, since correctness is only ever revealed once the quiz is
already finished.
"""
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.common import PyObjectId


class OptionOut(BaseModel):
    key: str
    text: str


class QuestionPublicOut(BaseModel):
    """Question as shown to a user actively taking a quiz.

    No correct_option, no seed_difficulty. Options are pre-reordered by the
    caller according to that attempt's persisted `option_order`.
    """

    id: PyObjectId
    chapter_id: PyObjectId
    text: str
    options: List[OptionOut]
    question_index: int
    total_questions: int


class QuestionReviewOut(BaseModel):
    """Per-question review shown on the result screen, once the quiz is
    complete -- correctness is only revealed here, never mid-quiz.
    """

    id: PyObjectId
    text: str
    options: List[OptionOut]
    correct_option: str
    selected_option: Optional[str]
    is_correct: Optional[bool]
