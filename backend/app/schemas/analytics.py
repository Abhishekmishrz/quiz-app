from typing import List, Optional

from pydantic import BaseModel


class LearningVelocityEntry(BaseModel):
    user_id: str
    user_name: str
    accuracy: float
    avg_response_time_ms: float
    consistency_score: float
    lvi: float
    rank: int


class FatigueBucket(BaseModel):
    bucket_index: int
    bucket_label: str
    accuracy: float
    avg_response_time_ms: float
    n_attempts_contributing: Optional[int] = None


class FatigueOut(BaseModel):
    mode: str  # "quiz_attempt" | "user"
    buckets: List[FatigueBucket]
    accuracy_delta: Optional[float]
    time_delta: Optional[float]
    accuracy_slope: Optional[float]
    time_slope: Optional[float]


class QuestionDifficultyEntry(BaseModel):
    question_id: str
    question_text: str
    chapter_id: str
    total_attempts: int
    raw_accuracy: float
    shrunk_accuracy: float
    avg_response_time_ms: float
    shrunk_time_ms: float
    qdi: float
    confidence: str
    rank: int


class ChapterMasteryEntry(BaseModel):
    chapter_id: str
    chapter_name: Optional[str] = None
    subject_id: Optional[str] = None
    total_attempts: int
    accuracy: float
    shrunk_accuracy: float
    avg_response_time_ms: float
    mastery_score: float


class SubjectMasteryRollup(BaseModel):
    subject_id: str
    subject_name: Optional[str] = None
    mastery_score: float
    total_attempts: int


class ChapterMasteryUserOut(BaseModel):
    mode: str = "user"
    user_id: str
    chapters: List[ChapterMasteryEntry]
    subjects: List[SubjectMasteryRollup]


class ChapterMasteryCohortEntry(BaseModel):
    user_id: str
    user_name: str
    total_attempts: int
    accuracy: float
    shrunk_accuracy: float
    avg_response_time_ms: float
    mastery_score: float
    rank: int


class ChapterMasteryCohortOut(BaseModel):
    mode: str = "chapter"
    chapter_id: str
    users: List[ChapterMasteryCohortEntry]
