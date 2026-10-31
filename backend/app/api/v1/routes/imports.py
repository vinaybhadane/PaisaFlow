"""API route handlers for statement ingestion, previews, and transactional confirmation."""

from typing import Optional
import uuid
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user_id
from backend.app.core.exceptions import ValidationError
from backend.app.db.dependencies import get_db
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.import_batch import (
    ImportBatchResponse,
    ImportConfirmRequest,
    ImportConfirmResponse,
    ImportPreviewResponse,
)
from backend.app.services.import_service import ImportService

router = APIRouter(prefix="/imports", tags=["Imports"])
import_service = ImportService()


@router.post(
    "",
    response_model=ApiResponse[ImportBatchResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload financial statement for parsing and normalization preview",
)
async def upload_statement(
    file: UploadFile = File(..., description="CSV or text-based PDF financial statement file"),
    account_id: Optional[uuid.UUID] = Form(None, description="Optional target account ID"),
    source_type: Optional[str] = Form(None, description="Optional hinted source type"),
    demo_profile_id: Optional[uuid.UUID] = Form(None, description="Optional synthetic persona ID"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ImportBatchResponse]:
    """Upload a synthetic bank or credit card statement.

    Parses tabular transactions, normalizes dates, currencies, and descriptions,
    flags potential duplicates, and prepares a non-destructive preview.
    """
    if not file.filename:
        raise ValidationError("Uploaded file must have a valid filename.")

    file_bytes = await file.read()
    batch = await import_service.create_import_job(
        db=db,
        user_id=user_id,
        filename=file.filename,
        file_bytes=file_bytes,
        account_id=account_id,
    )

    return ApiResponse(data=ImportBatchResponse.model_validate(batch))


@router.get(
    "/{import_id}",
    response_model=ApiResponse[ImportBatchResponse],
    summary="Get import batch status and summary",
)
async def get_import_status(
    import_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ImportBatchResponse]:
    """Retrieve the current processing status and row counts of an import batch."""
    batch = await import_service.get_import_batch(
        db=db,
        user_id=user_id,
        import_id=import_id,
    )
    return ApiResponse(data=ImportBatchResponse.model_validate(batch))


@router.get(
    "/{import_id}/preview",
    response_model=ApiResponse[ImportPreviewResponse],
    summary="Get parsed transaction candidates, warnings, and duplicate flags",
)
async def get_import_preview(
    import_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ImportPreviewResponse]:
    """Retrieve extracted and normalized transaction candidates for user review before committing."""
    preview = await import_service.get_import_preview(
        db=db,
        user_id=user_id,
        import_id=import_id,
    )
    return ApiResponse(data=preview)


@router.post(
    "/{import_id}/confirm",
    response_model=ApiResponse[ImportConfirmResponse],
    summary="Confirm selection and idempotently commit transactions to database",
)
async def confirm_import(
    import_id: uuid.UUID,
    request: ImportConfirmRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ImportConfirmResponse]:
    """Idempotently commit approved candidate transactions into user's ledger."""
    result = await import_service.confirm_import(
        db=db,
        user_id=user_id,
        import_id=import_id,
        request=request,
    )
    return ApiResponse(data=result)


@router.post(
    "/{import_id}/retry",
    response_model=ApiResponse[ImportBatchResponse],
    summary="Retry a safe reviewable or failed import job",
)
async def retry_import(
    import_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ImportBatchResponse]:
    """Re-check or reset a reviewable import batch."""
    batch = await import_service.get_import_batch(
        db=db,
        user_id=user_id,
        import_id=import_id,
    )
    if batch.status == "failed":
        batch.status = "preview_ready"
        batch.error_code = None
        batch.error_message = None
        await db.commit()
        await db.refresh(batch)

    return ApiResponse(data=ImportBatchResponse.model_validate(batch))

