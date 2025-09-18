"""
Extract endpoint for processing medical claim documents.
Enhanced with Prometheus metrics tracking.
"""

import time
from typing import Any, Dict

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from monitoring.prometheus_metrics import (
    ERROR_COUNTER,
    REQUEST_COUNTER,
    REQUEST_DURATION,
)
from src.core.exceptions import ExtractionError, OCRError, ValidationError
from src.core.logging_config import get_logger
from src.services.extraction_service import extract_claim_data
from src.services.ocr_service import ocr_image
from src.services.storage_service import store_claim
from src.utils.helpers import generate_document_id
from src.utils.validators import validate_upload_file


logger = get_logger(__name__)
router = APIRouter(prefix="/extract", tags=["extract"])


@router.post("", response_model=None)
async def extract_claim_document(file: UploadFile = File(...)) -> JSONResponse:
    """
    Extract structured data from an uploaded claim document.

    Accepts images (JPEG, PNG, BMP, TIFF) and PDF files.
    Returns JSON with extracted fields, _metadata, document_id and ocr_mode.
    """
    start_time = time.time()
    method = "POST"
    endpoint = "/extract"

    logger.info("Processing extract request for file: %s", file.filename)

    try:
        # Validate file
        validate_upload_file(file)

        # Read file content
        file_content = await file.read()
        logger.info("Read %d bytes from %s", len(file_content), file.filename)

        # Perform OCR
        logger.info("Starting OCR processing...")
        ocr_text, ocr_mode = ocr_image(
            file_content, file.filename or "unknown"
        )
        logger.info(
            "OCR completed using %s, extracted %d characters",
            ocr_mode,
            len(ocr_text),
        )

        # Extract structured data
        logger.info("Starting claim data extraction...")
        claim_data = extract_claim_data(ocr_text)
        logger.info("Claim data extraction completed")

        # Generate unique document ID
        document_id = generate_document_id()

        # Store and get enriched data with _metadata
        enriched = store_claim(document_id, claim_data)

        # Response with OCR mode
        response_data = {
            "document_id": document_id,
            "ocr_mode": ocr_mode,
            **enriched,
        }

        # Metrics
        REQUEST_COUNTER.labels(endpoint=endpoint, method=method).inc()
        REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(
            time.time() - start_time
        )

        logger.info(
            "Extract request completed successfully for document_id: %s",
            document_id,
        )
        return JSONResponse(status_code=200, content=response_data)

    except ValidationError as e:
        logger.error("Validation error: %s", e)
        ERROR_COUNTER.labels(
            endpoint=endpoint, method=method, error_type="ValidationError"
        ).inc()
        REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(
            time.time() - start_time
        )
        raise HTTPException(status_code=400, detail=str(e)) from e

    except OCRError as e:
        logger.error("OCR error: %s", e)
        ERROR_COUNTER.labels(
            endpoint=endpoint, method=method, error_type="OCRError"
        ).inc()
        REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(
            time.time() - start_time
        )
        raise HTTPException(
            status_code=422, detail=f"OCR processing failed: {str(e)}"
        ) from e

    except ExtractionError as e:
        logger.error("Extraction error: %s", e)
        ERROR_COUNTER.labels(
            endpoint=endpoint, method=method, error_type="ExtractionError"
        ).inc()
        REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(
            time.time() - start_time
        )
        raise HTTPException(
            status_code=422, detail=f"Data extraction failed: {str(e)}"
        ) from e

    except Exception as e:
        logger.error("Unexpected error during extraction: %s", e)
        ERROR_COUNTER.labels(
            endpoint=endpoint, method=method, error_type="UnexpectedError"
        ).inc()
        REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(
            time.time() - start_time
        )
        raise HTTPException(
            status_code=500, detail="Internal server error during extraction"
        ) from e


@router.get("/health")
async def extract_health_check() -> Dict[str, Any]:
    """Health check endpoint for the extract service."""
    return {
        "status": "healthy",
        "service": "extract",
        "message": "Extract endpoint is operational",
    }
