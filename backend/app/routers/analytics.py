from typing import List, Optional, Union

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.errors import ValidationAppError
from app.schemas.analytics import (
    ChapterMasteryCohortOut,
    ChapterMasteryUserOut,
    FatigueOut,
    LearningVelocityEntry,
    QuestionDifficultyEntry,
)
from app.schemas.common import PagedResponse
from app.services import analytics_service

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/learning-velocity", response_model=List[LearningVelocityEntry])
async def learning_velocity(db: AsyncIOMotorDatabase = Depends(get_db)):
    return await analytics_service.get_learning_velocity(db)


@router.get("/fatigue", response_model=FatigueOut)
async def fatigue(
    quiz_attempt_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return await analytics_service.get_fatigue(db, quiz_attempt_id=quiz_attempt_id, user_id=user_id)


@router.get("/question-difficulty", response_model=PagedResponse[QuestionDifficultyEntry])
async def question_difficulty(
    exam_id: Optional[str] = Query(None),
    subject_id: Optional[str] = Query(None),
    chapter_id: Optional[str] = Query(None),
    min_attempts: Optional[int] = Query(None, ge=0),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    result = await analytics_service.get_question_difficulty(
        db,
        exam_id=exam_id,
        subject_id=subject_id,
        chapter_id=chapter_id,
        min_attempts=min_attempts,
        limit=limit,
        offset=offset,
    )
    return PagedResponse[QuestionDifficultyEntry](**result)


@router.get("/chapter-mastery", response_model=Union[ChapterMasteryUserOut, ChapterMasteryCohortOut])
async def chapter_mastery(
    user_id: Optional[str] = Query(None),
    chapter_id: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if user_id:
        return await analytics_service.get_chapter_mastery_for_user(db, user_id)
    if chapter_id:
        return await analytics_service.get_chapter_mastery_for_chapter(db, chapter_id)
    raise ValidationAppError("Provide either user_id or chapter_id.", code="missing_filter")
