from typing import List

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.errors import NotFoundError
from app.repositories import chapter_repo, subject_repo
from app.schemas.chapter import ChapterOut

router = APIRouter(prefix="/api/v1/subjects", tags=["subjects"])


@router.get("/{subject_id}/chapters", response_model=List[ChapterOut])
async def list_chapters_for_subject(subject_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    subject = await subject_repo.get_subject_by_id(db, subject_id)
    if subject is None:
        raise NotFoundError("Subject not found.", code="subject_not_found")
    docs = await chapter_repo.list_chapters_for_subject(db, subject_id)
    return [
        ChapterOut(
            id=str(d["_id"]), subject_id=str(d["subject_id"]), exam_id=str(d["exam_id"]), name=d["name"], order=d["order"]
        )
        for d in docs
    ]
