"""Subject-scoped routes. The subject->chapters listing itself lives in
chapters.py (it's the "chapters" resource collection, just nested under a
subject) -- this module is kept for symmetry / future subject-only routes.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/subjects", tags=["subjects"])
