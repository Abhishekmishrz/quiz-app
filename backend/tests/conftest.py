"""Shared pytest fixtures.

`mongo_test_db` connects to a REAL MongoDB (MONGO_URI env var, defaulting to
mongodb://localhost:27017) and hands tests a throwaway database that's
dropped again in teardown. Tests that need this fixture (aggregation /
concurrency tests) are skipped automatically if no Mongo is reachable --
pure unit tests (test_stats.py, test_analytics_service.py) never touch this
fixture at all.
"""
import asyncio
import os
import uuid

import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError


def _mongo_uri() -> str:
    return os.environ.get("MONGO_URI", "mongodb://localhost:27017")


def _mongo_reachable() -> bool:
    async def _ping():
        client = AsyncIOMotorClient(_mongo_uri(), serverSelectionTimeoutMS=1500)
        try:
            await client.admin.command("ping")
        finally:
            client.close()

    try:
        asyncio.run(_ping())
        return True
    except Exception:
        return False


MONGO_AVAILABLE = _mongo_reachable()

requires_mongo = pytest.mark.skipif(
    not MONGO_AVAILABLE, reason="No reachable MongoDB instance (checked MONGO_URI / mongodb://localhost:27017)."
)


@pytest_asyncio.fixture
async def mongo_test_db():
    if not MONGO_AVAILABLE:
        pytest.skip("No reachable MongoDB instance.")

    db_name = f"quiz_app_test_{uuid.uuid4().hex[:10]}"
    client = AsyncIOMotorClient(_mongo_uri())
    db = client[db_name]
    try:
        yield db
    finally:
        await client.drop_database(db_name)
        client.close()
