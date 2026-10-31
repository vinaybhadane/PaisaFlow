"""Initialize local development database with tables and synthetic demo personas."""

import asyncio
from backend.app.db.base import Base
from backend.app.db.session import AsyncSessionLocal, engine
import backend.app.models  # noqa
from backend.app.services.demo_data_service import DemoDataService


async def init_dev():
    print("Creating all tables in database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully.")

    print("Seeding synthetic demo personas...")
    async with AsyncSessionLocal() as session:
        service = DemoDataService(seed=42)
        summary = await service.seed_all(session)
        print("Seeding complete:", summary["personas_seeded"])


if __name__ == "__main__":
    asyncio.run(init_dev())

