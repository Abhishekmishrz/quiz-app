"""Motor (async) MongoDB client — cached at module scope.

The client is created lazily on first access and never re-created per
request/invocation. This matters both for ordinary efficiency and,
specifically, because this backend is designed to also run on Vercel
serverless functions where creating a new client per invocation would
quickly exhaust MongoDB Atlas's free-tier connection cap. Re-using the
client across warm invocations of the same container keeps connection
count bounded.
"""
import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

logger = logging.getLogger("quiz_app")

# Module-scope cache. Intentionally NOT recreated per request.
_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGO_URI)
    return _client


def get_database() -> AsyncIOMotorDatabase:
    return get_client()[settings.DB_NAME]


async def get_db() -> AsyncIOMotorDatabase:
    """FastAPI dependency yielding the cached database handle."""
    return get_database()


async def create_indexes() -> None:
    """Idempotently create all indexes described in the schema spec.

    Safe to call on every startup -- `create_index` is a no-op if an
    equivalent index already exists.
    """
    db = get_database()

    await db.subjects.create_index("exam_id")

    await db.chapters.create_index("subject_id")

    await db.questions.create_index("chapter_id")

    await db.quiz_attempts.create_index([("user_id", 1), ("status", 1)])
    await db.quiz_attempts.create_index([("user_id", 1), ("started_at", -1)])

    await db.question_events.create_index(
        [("quiz_attempt_id", 1), ("question_id", 1)], unique=True
    )
    await db.question_events.create_index([("quiz_attempt_id", 1), ("question_index", 1)])
    await db.question_events.create_index([("user_id", 1), ("submitted_at", -1)])
    await db.question_events.create_index("question_id")
    await db.question_events.create_index("chapter_id")
    await db.question_events.create_index([("exam_id", 1), ("subject_id", 1), ("chapter_id", 1)])
    await db.question_events.create_index([("user_id", 1), ("chapter_id", 1)])

    await db.users.create_index("email", unique=True)

    logger.info("MongoDB indexes ensured.")


async def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
