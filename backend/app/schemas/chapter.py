from pydantic import BaseModel

from app.schemas.common import PyObjectId


class ChapterOut(BaseModel):
    id: PyObjectId
    subject_id: PyObjectId
    exam_id: PyObjectId
    name: str
    order: int
