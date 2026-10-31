"""API v1 consolidated router."""

from fastapi import APIRouter
from backend.app.api.v1.routes.categories import router as categories_router
from backend.app.api.v1.routes.categorization_rules import router as categorization_rules_router
from backend.app.api.v1.routes.coach import router as coach_router
from backend.app.api.v1.routes.config import router as config_router
from backend.app.api.v1.routes.forecast import router as forecast_router
from backend.app.api.v1.routes.health import router as health_router
from backend.app.api.v1.routes.imports import router as imports_router
from backend.app.api.v1.routes.insights import router as insights_router
from backend.app.api.v1.routes.merchants import router as merchants_router
from backend.app.api.v1.routes.profile import router as profile_router, summary_router as financial_summary_router
from backend.app.api.v1.routes.recurring import router as recurring_router
from backend.app.api.v1.routes.simulations import router as simulations_router
from backend.app.api.v1.routes.spending import router as spending_router
from backend.app.api.v1.routes.transactions import router as transactions_router

api_v1_router = APIRouter()

api_v1_router.include_router(health_router)
api_v1_router.include_router(config_router)
api_v1_router.include_router(categories_router)
api_v1_router.include_router(merchants_router)
api_v1_router.include_router(imports_router)
api_v1_router.include_router(transactions_router)
api_v1_router.include_router(categorization_rules_router)
api_v1_router.include_router(recurring_router)
api_v1_router.include_router(profile_router)
api_v1_router.include_router(financial_summary_router)
api_v1_router.include_router(insights_router)
api_v1_router.include_router(spending_router)
api_v1_router.include_router(forecast_router)
api_v1_router.include_router(simulations_router)
api_v1_router.include_router(coach_router)
