import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.schemas.invoice import ExtractionResult
from app.services.documents import DocumentError, UnsupportedDocumentError
from app.services.extraction import InvoiceExtractor
from app.services.llm import ExtractionError, OpenRouterClient

logger = logging.getLogger(__name__)

router = APIRouter()


@lru_cache
def _build_extractor() -> InvoiceExtractor:
    settings = get_settings()
    return InvoiceExtractor(settings, OpenRouterClient(settings))


def get_extractor() -> InvoiceExtractor:
    if not get_settings().extraction_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Extraction is disabled in this environment.",
        )
    try:
        return _build_extractor()
    except ExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


# A plain `def` runs in FastAPI's thread pool, so OCR and the model call do not block the event loop.
# Moves to a background worker in Phase 2.
@router.post("", response_model=ExtractionResult)
def create_extraction(file: UploadFile, extractor: InvoiceExtractor = Depends(get_extractor)) -> ExtractionResult:
    max_bytes = get_settings().max_upload_bytes
    data = file.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Files are limited to {max_bytes // (1024 * 1024)} MB.",
        )
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The file is empty.")

    try:
        result = extractor.extract(data)
    except UnsupportedDocumentError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)) from exc
    except DocumentError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    logger.info("Extraction finished: status=%s issues=%d", result.status, len(result.issues))
    return result
