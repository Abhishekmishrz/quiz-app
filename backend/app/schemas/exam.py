from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import PyObjectId


class ExamOut(BaseModel):
    id: PyObjectId
    name: str
    code: str
    created_at: datetime
