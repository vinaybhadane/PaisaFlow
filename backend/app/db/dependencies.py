"""Database session dependencies for route handlers."""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining an isolated async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

