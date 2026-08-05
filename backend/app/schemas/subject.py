from pydantic import BaseModel

from app.schemas.common import PyObjectId


class SubjectOut(BaseModel):
    id: PyObjectId
    exam_id: PyObjectId
    name: str
    code: str
    order: int
