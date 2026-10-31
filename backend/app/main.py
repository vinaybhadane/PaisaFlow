"""PaisaFlow FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import uuid
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.v1.router import api_v1_router
from backend.app.api.v1.routes.health import health_check
from backend.app.core.config import settings
from backend.app.core.exceptions import PaisaFlowException
from backend.app.core.logging import logger, setup_logging
from backend.app.schemas.common import ApiError, ApiErrorResponse, ApiMeta, ApiResponse
from backend.app.schemas.health import HealthData


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown procedures."""
    setup_logging(log_level="DEBUG" if settings.APP_ENV == "development" else "INFO")
    logger.info(f"Starting {settings.PROJECT_NAME} in '{settings.APP_ENV}' environment...")
    logger.info(f"CORS origins configured: {settings.CORS_ORIGINS}")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="PaisaFlow — AI-Powered Personal Finance Coach with a Living Money Model.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(PaisaFlowException)
async def domain_exception_handler(request: Request, exc: PaisaFlowException) -> JSONResponse:
    """Handle custom PaisaFlow domain exceptions."""
    request_id = str(uuid.uuid4())
    logger.warning(f"Domain exception [{exc.code}] on {request.method} {request.url.path}: {exc.message}")

    error_response = ApiErrorResponse(
        error=ApiError(
            code=exc.code,
            message=exc.message,
            details=exc.details,
        ),
        meta=ApiMeta(request_id=request_id),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic request validation errors."""
    request_id = str(uuid.uuid4())
    logger.info(f"Request validation failure on {request.method} {request.url.path}: {exc.errors()}")

    details = [
        {
            "field": ".".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
            "type": err["type"],
        }
        for err in exc.errors()
    ]

    error_response = ApiErrorResponse(
        error=ApiError(
            code="VALIDATION_ERROR",
            message="Request input validation failed.",
            details=details,
        ),
        meta=ApiMeta(request_id=request_id),
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all error handler ensuring no internal stack traces or secrets leak."""
    request_id = str(uuid.uuid4())
    logger.error(f"Unhandled server error on {request.method} {request.url.path}: {exc}", exc_info=True)

    error_response = ApiErrorResponse(
        error=ApiError(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred. Please try again later.",
            details=[],
        ),
        meta=ApiMeta(request_id=request_id),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
    )


# Root level /health route
app.add_api_route(
    "/health",
    health_check,
    methods=["GET"],
    response_model=ApiResponse[HealthData],
    tags=["Health"],
    summary="Application Health Check",
)

# API v1 routes
app.include_router(api_v1_router, prefix=settings.API_V1_STR)

