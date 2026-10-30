import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.database.db import get_db


# Load the project .env so the test suite can read TEST_DATABASE_URL.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL must be set before running tests.")


@pytest.fixture
def anyio_backend():
    # asyncpg and asyncio.gather in these tests use the asyncio backend.
    return "asyncio"


@pytest.fixture
async def test_session_factory(anyio_backend):
    # Each test gets its own engine; concurrent tasks get separate sessions
    # from this shared factory.
    engine = create_async_engine(str(TEST_DATABASE_URL), echo=False)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )

    try:
        yield session_factory
    finally:
        await engine.dispose()
