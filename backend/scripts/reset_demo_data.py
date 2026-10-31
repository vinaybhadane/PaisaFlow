"""Executable script to safely reset ONLY synthetic demo data."""

import asyncio
import sys
from backend.app.core.logging import logger, setup_logging
from backend.app.db.session import AsyncSessionLocal, check_db_connectivity
from backend.app.services.demo_data_service import DemoDataService


async def main() -> None:
    setup_logging()
    logger.info("Initializing synthetic demo data reset...")

    is_connected = await check_db_connectivity()
    if not is_connected:
        logger.error(
            "Cannot connect to the configured PostgreSQL database. "
            "Please ensure the database is running and DATABASE_URL is properly configured."
        )
        sys.exit(1)

    async with AsyncSessionLocal() as session:
        service = DemoDataService()
        result = await service.reset_synthetic_demo_data(session)
        logger.info(f"Reset completed: {result}")


if __name__ == "__main__":
    asyncio.run(main())

