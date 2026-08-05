"""FastAPI application factory: CORS, routers, index creation on startup,
and registration of the custom exception handlers.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_indexes
from app.core.errors import register_exception_handlers
from app.routers import analytics, chapters, exams, quiz_attempts, sessions, subjects, users

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("quiz_app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_indexes()
    logger.info("Application startup complete.")
    yield


app = FastAPI(
    title="WhatsApp-style Quiz Application API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(users.router)
app.include_router(sessions.router)
app.include_router(exams.router)
app.include_router(subjects.router)
app.include_router(chapters.router)
app.include_router(quiz_attempts.router)
app.include_router(analytics.router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
