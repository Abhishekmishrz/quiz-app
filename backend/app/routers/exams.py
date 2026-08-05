from typing import List

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.errors import NotFoundError
from app.repositories import exam_repo, subject_repo
from app.schemas.exam import ExamOut
from app.schemas.subject import SubjectOut

router = APIRouter(prefix="/api/v1/exams", tags=["exams"])


@router.get("", response_model=List[ExamOut])
async def list_exams(db: AsyncIOMotorDatabase = Depends(get_db)):
    docs = await exam_repo.list_exams(db)
    return [ExamOut(id=str(d["_id"]), **{k: v for k, v in d.items() if k != "_id"}) for d in docs]


@router.get("/{exam_id}/subjects", response_model=List[SubjectOut])
async def list_subjects_for_exam(exam_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    exam = await exam_repo.get_exam_by_id(db, exam_id)
    if exam is None:
        raise NotFoundError("Exam not found.", code="exam_not_found")
    docs = await subject_repo.list_subjects_for_exam(db, exam_id)
    return [
        SubjectOut(id=str(d["_id"]), exam_id=str(d["exam_id"]), name=d["name"], code=d["code"], order=d["order"])
        for d in docs
    ]
