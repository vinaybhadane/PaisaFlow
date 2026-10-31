"""Scenario persistence service and multi-scenario comparison."""

from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import NotFoundError, ValidationError
from backend.app.models.scenario import Scenario


class ScenarioService:
    """Service managing saved what-if simulation records."""

    async def create_scenario(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        title: str,
        scenario_type: str,
        input_parameters: Dict[str, Any],
        baseline_result: Dict[str, Any],
        scenario_result: Dict[str, Any],
        assumptions: Dict[str, Any],
        calculation_version: str = "1.0.0",
    ) -> Scenario:
        """Save a what-if simulation record."""
        clean_title = title.strip()
        if not clean_title:
            raise ValidationError("Scenario title cannot be empty.")

        scenario = Scenario(
            user_id=user_id,
            title=clean_title,
            scenario_type=scenario_type,
            input_parameters=input_parameters,
            baseline_result=baseline_result,
            scenario_result=scenario_result,
            assumptions=assumptions,
            calculation_version=calculation_version,
        )
        db.add(scenario)
        await db.commit()
        await db.refresh(scenario)
        return scenario

    async def list_user_scenarios(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> List[Scenario]:
        """List all scenarios saved by the user."""
        stmt = (
            select(Scenario)
            .where(Scenario.user_id == user_id)
            .order_by(Scenario.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_scenario_by_id(
        self, db: AsyncSession, user_id: uuid.UUID, scenario_id: uuid.UUID
    ) -> Scenario:
        """Retrieve a specific scenario ensuring strict user ownership."""
        stmt = select(Scenario).where(
            Scenario.id == scenario_id,
            Scenario.user_id == user_id,
        )
        res = await db.execute(stmt)
        scenario = res.scalar_one_or_none()
        if not scenario:
            raise NotFoundError(f"Scenario {scenario_id} not found.")
        return scenario

    async def update_scenario(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        scenario_id: uuid.UUID,
        title: Optional[str] = None,
    ) -> Scenario:
        """Update a scenario title."""
        scenario = await self.get_scenario_by_id(db, user_id, scenario_id)
        if title is not None:
            clean = title.strip()
            if not clean:
                raise ValidationError("Title cannot be empty.")
            scenario.title = clean

        await db.commit()
        await db.refresh(scenario)
        return scenario

    async def delete_scenario(
        self, db: AsyncSession, user_id: uuid.UUID, scenario_id: uuid.UUID
    ) -> bool:
        """Delete a scenario record."""
        scenario = await self.get_scenario_by_id(db, user_id, scenario_id)
        await db.delete(scenario)
        await db.commit()
        return True

    async def compare_scenarios(
        self, db: AsyncSession, user_id: uuid.UUID, scenario_ids: List[uuid.UUID]
    ) -> Dict[str, Any]:
        """Compare multiple saved scenarios side-by-side."""
        if not scenario_ids:
            raise ValidationError("At least one scenario ID must be provided for comparison.")

        stmt = select(Scenario).where(
            Scenario.user_id == user_id,
            Scenario.id.in_(scenario_ids),
        )
        res = await db.execute(stmt)
        scenarios = list(res.scalars().all())

        if len(scenarios) != len(scenario_ids):
            raise NotFoundError("One or more scenarios not found or not owned by user.")

        comparison_items = []
        for s in scenarios:
            delta = s.scenario_result.get("delta", {})
            comparison_items.append(
                {
                    "id": str(s.id),
                    "title": s.title,
                    "scenario_type": s.scenario_type,
                    "monthly_delta": delta.get("available_money_delta", "0.00"),
                    "twelve_month_impact": s.scenario_result.get("period_impacts", {}).get(
                        "twelve_month_impact", "0.00"
                    ),
                    "updated_savings_rate": s.scenario_result.get("scenario", {}).get(
                        "savings_rate", "0.00"
                    ),
                }
            )

        return {
            "user_id": str(user_id),
            "scenario_count": len(scenarios),
            "scenarios": comparison_items,
        }

