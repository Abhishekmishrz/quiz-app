"""Vercel ASGI entrypoint -- no serverless-specific logic, just re-exports
the same FastAPI app used locally and in Docker."""
from app.main import app  # noqa: F401
