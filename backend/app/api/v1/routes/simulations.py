"""API route handlers for What-If scenario simulations, execution, and persistence."""

from typing import List
import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user_id
from backend.app.db.dependencies import get_db
from backend.app.intelligence.simulations.scenario_service import ScenarioService
from backend.app.intelligence.simulations.simulation_engine import SimulationEngine
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.simulation import (
    ScenarioCompareRequest,
    ScenarioComparisonItem,
    ScenarioComparisonResponse,
    ScenarioCreateRequest,
    ScenarioPeriodImpactsResponse,
    ScenarioResponse,
    ScenarioRunRequest,
    ScenarioUpdateRequest,
    SimulationRunResponse,
)

router = APIRouter(prefix="/simulations", tags=["What-If Simulations"])
engine = SimulationEngine()
service = ScenarioService()


@router.post(
    "/run",
    response_model=ApiResponse[SimulationRunResponse],
    summary="Execute an on-the-fly what-if scenario simulation against baseline",
)
async def run_simulation(
    payload: ScenarioRunRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SimulationRunResponse]:
    """Calculate deterministic financial impacts of hypothetical changes across 3, 6, and 12 months.

    Original transaction records and living facts remain completely unchanged.
    """
    res = await engine.run_simulation(
        db,
        user_id,
        scenario_type=payload.scenario_type,
        input_parameters=payload.input_parameters,
        period_start=payload.period_start,
        period_end=payload.period_end,
    )

    impacts = ScenarioPeriodImpactsResponse(
        monthly_delta=res.period_impacts.monthly_delta,
        three_month_impact=res.period_impacts.three_month_impact,
        six_month_impact=res.period_impacts.six_month_impact,
        twelve_month_impact=res.period_impacts.twelve_month_impact,
    )

    data = SimulationRunResponse(
        scenario_type=res.scenario_type,
        title=res.title,
        currency=res.currency,
        baseline=res.baseline,
        scenario=res.scenario,
        delta=res.delta,
        period_impacts=impacts,
        assumptions=res.assumptions,
        notes=res.notes,
        calculation_version=res.calculation_version,
    )
    return ApiResponse(data=data)


@router.post(
    "",
    response_model=ApiResponse[ScenarioResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Save a what-if scenario record to user profile",
)
async def save_scenario(
    payload: ScenarioCreateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ScenarioResponse]:
    """Save a what-if simulation result for future comparison."""
    scenario = await service.create_scenario(
        db=db,
        user_id=user_id,
        title=payload.title,
        scenario_type=payload.scenario_type,
        input_parameters=payload.input_parameters,
        baseline_result=payload.baseline_result,
        scenario_result=payload.scenario_result,
        assumptions=payload.assumptions,
        calculation_version=payload.calculation_version,
    )
    return ApiResponse(data=ScenarioResponse.model_validate(scenario))


@router.get(
    "",
    response_model=ApiResponse[List[ScenarioResponse]],
    summary="List all saved what-if scenarios for user",
)
async def list_scenarios(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[List[ScenarioResponse]]:
    """Retrieve all user-saved scenarios."""
    scenarios = await service.list_user_scenarios(db, user_id)
    return ApiResponse(data=[ScenarioResponse.model_validate(s) for s in scenarios])


@router.get(
    "/{scenario_id}",
    response_model=ApiResponse[ScenarioResponse],
    summary="Get saved scenario detail",
)
async def get_scenario(
    scenario_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ScenarioResponse]:
    """Retrieve details of a specific saved scenario."""
    scenario = await service.get_scenario_by_id(db, user_id, scenario_id)
    return ApiResponse(data=ScenarioResponse.model_validate(scenario))


@router.patch(
    "/{scenario_id}",
    response_model=ApiResponse[ScenarioResponse],
    summary="Update saved scenario title",
)
async def update_scenario(
    scenario_id: uuid.UUID,
    payload: ScenarioUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ScenarioResponse]:
    """Update title of an existing saved scenario."""
    scenario = await service.update_scenario(
        db, user_id, scenario_id, title=payload.title
    )
    return ApiResponse(data=ScenarioResponse.model_validate(scenario))


@router.delete(
    "/{scenario_id}",
    response_model=ApiResponse[dict],
    summary="Delete a saved what-if scenario",
)
async def delete_scenario(
    scenario_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """Delete a saved scenario record."""
    await service.delete_scenario(db, user_id, scenario_id)
    return ApiResponse(data={"status": "deleted", "id": str(scenario_id)})


@router.post(
    "/compare",
    response_model=ApiResponse[ScenarioComparisonResponse],
    summary="Compare multiple saved scenarios side-by-side",
)
async def compare_scenarios(
    payload: ScenarioCompareRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ScenarioComparisonResponse]:
    """Build side-by-side comparison matrix across multiple saved scenarios."""
    res = await service.compare_scenarios(db, user_id, payload.scenario_ids)
    items = [
        ScenarioComparisonItem(
            id=s["id"],
            title=s["title"],
            scenario_type=s["scenario_type"],
            monthly_delta=s["monthly_delta"],
            twelve_month_impact=s["twelve_month_impact"],
            updated_savings_rate=s["updated_savings_rate"],
        )
        for s in res["scenarios"]
    ]
    return ApiResponse(
        data=ScenarioComparisonResponse(
            user_id=user_id,
            scenario_count=res["scenario_count"],
            scenarios=items,
        )
    )

