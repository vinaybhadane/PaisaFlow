"""Safe frontend public configuration route handler."""

from fastapi import APIRouter
from backend.app.core.config import settings
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.config import ConfigData

router = APIRouter(tags=["Config"])


@router.get("/config", response_model=ApiResponse[ConfigData])
async def get_public_config() -> ApiResponse[ConfigData]:
    """Return public application parameters for frontend clients without secrets."""
    data = ConfigData(
        app_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.APP_ENV,
        default_currency=settings.DEFAULT_CURRENCY,
        default_locale=settings.DEFAULT_LOCALE,
        default_timezone=settings.DEFAULT_TIMEZONE,
        supported_upload_formats=settings.SUPPORTED_UPLOAD_FORMATS,
        max_upload_size_bytes=settings.MAX_UPLOAD_SIZE_BYTES,
        is_synthetic_only=True,
        features={
            "what_if_simulation": True,
            "living_money_model": True,
            "ai_coach": True,
            "offline_mode": False,
            "real_bank_connection": False,
        },
    )

    return ApiResponse(data=data)

