"""Database session and connection engine management."""

import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.core.config import settings
from backend.app.core.logging import logger

# Asynchronous engine configuration (supports PostgreSQL pooling & local SQLite fallback)
engine_kwargs = {"echo": False, "pool_pre_ping": True}
if "postgresql" in settings.DATABASE_URL:
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    if "pooler.supabase.com" in settings.DATABASE_URL:
        engine_kwargs["connect_args"] = {"prepared_statement_cache_size": 0}

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def check_db_connectivity(timeout_seconds: float = 15.0) -> bool:
    """Check if the database can be reached and execute a ping query."""
    try:
        async with asyncio.timeout(timeout_seconds):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                return True
    except Exception as e:
        logger.warning(f"Database connectivity check failed: {repr(e)}")
        import traceback
        traceback.print_exc()
        return False
