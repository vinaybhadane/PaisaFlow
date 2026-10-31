"""Health check route handlers."""

from fastapi import APIRouter
from backend.app.core.config import settings
from backend.app.db.session import check_db_connectivity
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.health import HealthData

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=ApiResponse[HealthData])
async def health_check() -> ApiResponse[HealthData]:
    """Return application and database health status without disclosing internal credentials."""
    is_db_connected = await check_db_connectivity(timeout_seconds=15.0)

    data = HealthData(
        status="healthy" if is_db_connected else "degraded",
        app_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.APP_ENV,
        database="connected" if is_db_connected else "unavailable",
    )

    return ApiResponse(data=data)

