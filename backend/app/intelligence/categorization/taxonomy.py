"""Canonical category taxonomy definition, hierarchy management, and idempotent seeding."""

from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.category import Category

# Canonical PaisaFlow Category Taxonomy Specification
# Structure: (parent_name, category_type, sort_order, [(child_name, sort_order), ...])
TAXONOMY_SPEC: List[Dict[str, Any]] = [
    {
        "name": "Income",
        "type": "income",
        "sort_order": 10,
        "children": [
            ("Salary", 11),
            ("Freelance & Invoicing", 12),
            ("Investments & Dividends", 13),
            ("Interest & Rewards", 14),
            ("Other Income", 19),
        ],
    },
    {
        "name": "Refunds",
        "type": "income",  # Inflows, but isolated from salary/ordinary income
        "sort_order": 20,
        "children": [
            ("Merchant Refund", 21),
            ("Cashback & Rebates", 22),
            ("Tax Refund", 23),
        ],
    },
    {
        "name": "Transfers",
        "type": "transfer",
        "sort_order": 30,
        "children": [
            ("Own Account Transfer", 31),
            ("Credit Card Bill Payment", 32),
            ("Peer-to-Peer Transfer", 33),
        ],
    },
    {
        "name": "Housing & Rent",
        "type": "expense",
        "sort_order": 40,
        "children": [
            ("Rent", 41),
            ("Maintenance & Society", 42),
            ("Property Tax", 43),
        ],
    },
    {
        "name": "Utilities",
        "type": "expense",
        "sort_order": 50,
        "children": [
            ("Electricity", 51),
            ("Water", 52),
            ("Gas & Fuel", 53),
            ("Broadband & Mobile", 54),
        ],
    },
    {
        "name": "Food & Dining",
        "type": "expense",
        "sort_order": 60,
        "children": [
            ("Groceries", 61),
            ("Food Delivery", 62),
            ("Restaurants & Cafes", 63),
        ],
    },
    {
        "name": "Transportation",
        "type": "expense",
        "sort_order": 70,
        "children": [
            ("Ride Hailing & Taxi", 71),
            ("Public Transit", 72),
            ("Fuel & Fastag", 73),
            ("Vehicle Maintenance", 74),
        ],
    },
    {
        "name": "Shopping",
        "type": "expense",
        "sort_order": 80,
        "children": [
            ("Clothing & Apparel", 81),
            ("Electronics & Gadgets", 82),
            ("Home & Living", 83),
            ("General Retail", 84),
        ],
    },
    {
        "name": "Healthcare",
        "type": "expense",
        "sort_order": 90,
        "children": [
            ("Pharmacy & Medicines", 91),
            ("Doctor & Clinic", 92),
            ("Health Insurance", 93),
            ("Fitness & Wellness", 94),
        ],
    },
    {
        "name": "Education",
        "type": "expense",
        "sort_order": 100,
        "children": [
            ("Tuition & School", 101),
            ("Books & Courses", 102),
        ],
    },
    {
        "name": "Entertainment & Subscriptions",
        "type": "expense",
        "sort_order": 110,
        "children": [
            ("Streaming Services", 111),
            ("Movies & Events", 112),
            ("Software & Cloud Storage", 113),
            ("Gaming", 114),
        ],
    },
    {
        "name": "Travel",
        "type": "expense",
        "sort_order": 120,
        "children": [
            ("Flights & Trains", 121),
            ("Hotels & Stays", 122),
        ],
    },
    {
        "name": "Financial Charges",
        "type": "expense",
        "sort_order": 130,
        "children": [
            ("Bank Charges & Fees", 131),
            ("Interest & Finance Fees", 132),
            ("Late Payment Penalty", 133),
        ],
    },
    {
        "name": "Investments",
        "type": "expense",
        "sort_order": 140,
        "children": [
            ("Mutual Funds & SIP", 141),
            ("Stocks & Equities", 142),
            ("Fixed Deposits & PPF", 143),
        ],
    },
    {
        "name": "Other",
        "type": "expense",
        "sort_order": 990,
        "children": [
            ("Uncategorized Expense", 991),
        ],
    },
]


class CategoryTaxonomyService:
    """Manages category queries, hierarchical tree construction, and seeding."""

    @classmethod
    async def seed_system_categories(cls, session: AsyncSession) -> Dict[str, Category]:
        """Idempotently initialize the canonical taxonomy.

        Creates parents first, then creates or attaches subcategories.
        Guarantees that repeated executions never duplicate records.
        """
        existing_res = await session.execute(select(Category))
        existing_cats = {c.name.lower(): c for c in existing_res.scalars().all()}

        categories_by_name: Dict[str, Category] = {}

        # 1. Seed or retrieve top-level parent categories
        for spec in TAXONOMY_SPEC:
            name = spec["name"]
            key = name.lower()
            if key in existing_cats:
                parent = existing_cats[key]
                parent.category_type = spec["type"]
                parent.sort_order = spec["sort_order"]
                parent.is_system = True
            else:
                parent = Category(
                    id=uuid.uuid4(),
                    name=name,
                    category_type=spec["type"],
                    sort_order=spec["sort_order"],
                    is_system=True,
                )
                session.add(parent)
                await session.flush()
                existing_cats[key] = parent

            categories_by_name[name] = parent

            # 2. Seed or retrieve child subcategories
            for child_name, child_order in spec["children"]:
                child_key = child_name.lower()
                if child_key in existing_cats:
                    child = existing_cats[child_key]
                    child.parent_id = parent.id
                    child.category_type = spec["type"]
                    child.sort_order = child_order
                    child.is_system = True
                else:
                    child = Category(
                        id=uuid.uuid4(),
                        parent_id=parent.id,
                        name=child_name,
                        category_type=spec["type"],
                        sort_order=child_order,
                        is_system=True,
                    )
                    session.add(child)
                    await session.flush()
                    existing_cats[child_key] = child

                categories_by_name[child_name] = child

        await session.commit()
        return categories_by_name

    @classmethod
    async def get_taxonomy_tree(cls, session: AsyncSession) -> List[Category]:
        """Retrieve root categories with populated subcategories ordered by sort_order."""
        stmt = (
            select(Category)
            .where(Category.parent_id.is_(None))
            .options(selectinload(Category.subcategories))
            .order_by(Category.sort_order.asc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def get_all_categories(cls, session: AsyncSession) -> List[Category]:
        """Retrieve all active categories ordered by sort_order."""
        stmt = select(Category).order_by(Category.sort_order.asc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def get_by_id(cls, session: AsyncSession, category_id: uuid.UUID) -> Optional[Category]:
        """Fetch category by UUID."""
        stmt = select(Category).where(Category.id == category_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_name(cls, session: AsyncSession, name: str) -> Optional[Category]:
        """Case-insensitive category lookup by name."""
        stmt = select(Category).where(Category.name.ilike(name.strip()))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

