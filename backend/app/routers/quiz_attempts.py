from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.schemas.quiz_attempt import (
    AnswerResultOut,
    AnswerSubmit,
    QuizAttemptCreate,
    QuizAttemptStartOut,
    QuizResultOut,
)
from app.schemas.question import QuestionPublicOut
from app.services import quiz_service

router = APIRouter(prefix="/api/v1/quiz-attempts", tags=["quiz-attempts"])


@router.post("", response_model=QuizAttemptStartOut)
async def start_or_resume_attempt(
    payload: QuizAttemptCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    result = await quiz_service.start_or_resume_attempt(db, user_id, payload.chapter_id)
    return result


@router.get("/{attempt_id}/current-question", response_model=QuestionPublicOut)
async def get_current_question(
    attempt_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return await quiz_service.get_current_question(db, attempt_id, user_id)


@router.post("/{attempt_id}/answers", response_model=AnswerResultOut)
async def submit_answer(
    attempt_id: str,
    payload: AnswerSubmit,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return await quiz_service.submit_answer(db, attempt_id, user_id, payload.question_id, payload.selected_option)


@router.get("/{attempt_id}/result", response_model=QuizResultOut)
async def get_result(
    attempt_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return await quiz_service.get_result(db, attempt_id, user_id)
