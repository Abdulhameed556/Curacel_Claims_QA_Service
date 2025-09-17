
"""
Extract endpoint for processing medical claim documents.
Enhanced with Prometheus metrics tracking.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any
import time

from src.services.ocr_service import ocr_image
from src.services.extraction_service import extract_claim_data
from src.services.storage_service import store_claim
from src.utils.helpers import generate_document_id
from src.utils.validators import validate_upload_file
from src.core.exceptions import OCRError, ExtractionError, ValidationError
from src.core.logging_config import get_logger
from src.core.config import settings

# Import Prometheus metrics
from monitoring.prometheus_metrics import (
    REQUEST_COUNTER,
    REQUEST_DURATION,
    ERROR_COUNTER,
    DOCUMENTS_PROCESSED
)

logger = get_logger(__name__)
router = APIRouter(prefix="/extract", tags=["extract"])


@router.post("", response_model=None)
async def extract_claim_document(file: UploadFile = File(...)) -> JSONResponse:
    """
    Extract structured data from uploaded medical claim document.
    
    Accepts:
    - Image files (JPEG, PNG, BMP, TIFF)
    - PDF files
    
    Returns:
    - JSON object with extracted claim data and document_id for future reference
    
    Process:
    1. Validate uploaded file
    2. Perform OCR using Gemini Vision API or fallback
    3. Extract structured data (patient, medications, diagnoses, etc.)
    4. Store in memory for future /ask queries
    5. Return structured data with document_id
    """
    start_time = time.time()
    method = "POST"
    endpoint = "/extract"

    logger.info(f"Processing extract request for file: {file.filename}")
    
    try:
        # Validate file
        validate_upload_file(file)
        
        # Read file content
        file_content = await file.read()
        logger.info(f"Read {len(file_content)} bytes from {file.filename}")
        
        # Perform OCR
        logger.info("Starting OCR processing...")
        ocr_text, ocr_mode = ocr_image(file_content, file.filename or "unknown")
        logger.info(f"OCR completed using {ocr_mode}, extracted {len(ocr_text)} characters")
        
        # Extract structured data
        logger.info("Starting claim data extraction...")
        claim_data = extract_claim_data(ocr_text)
        logger.info("Claim data extraction completed")
        
        # Generate unique document ID
        document_id = generate_document_id()
        
        # Store in memory for future /ask queries (this will increment DOCUMENTS_PROCESSED and update DOCUMENTS_IN_STORAGE)
        store_claim(document_id, claim_data)
        
        # Prepare response with actual OCR mode used
        response_data = {
            "document_id": document_id,
            "ocr_mode": ocr_mode,
            **claim_data
        }
        
        # Metrics: successful request
        REQUEST_COUNTER.labels(endpoint=endpoint, method=method).inc()
        REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(time.time() - start_time)
        
        logger.info(f"Extract request completed successfully for document_id: {document_id}")
        return JSONResponse(
            status_code=200,
            content=response_data
        )
        
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        ERROR_COUNTER.labels(endpoint=endpoint, method=method, error_type="ValidationError").inc()
        REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(time.time() - start_time)
        raise HTTPException(status_code=400, detail=str(e))
        
    except OCRError as e:
        logger.error(f"OCR error: {str(e)}")
        ERROR_COUNTER.labels(endpoint=endpoint, method=method, error_type="OCRError").inc()
        REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(time.time() - start_time)
        raise HTTPException(status_code=422, detail=f"OCR processing failed: {str(e)}")
        
    except ExtractionError as e:
        logger.error(f"Extraction error: {str(e)}")
        ERROR_COUNTER.labels(endpoint=endpoint, method=method, error_type="ExtractionError").inc()
        REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(time.time() - start_time)
        raise HTTPException(status_code=422, detail=f"Data extraction failed: {str(e)}")
        
    except Exception as e:
        logger.error(f"Unexpected error during extraction: {str(e)}")
        ERROR_COUNTER.labels(endpoint=endpoint, method=method, error_type="UnexpectedError").inc()
        REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(time.time() - start_time)
        raise HTTPException(status_code=500, detail="Internal server error during extraction")
        

@router.get("/health")
async def extract_health_check() -> Dict[str, Any]:
    """Health check endpoint for the extract service."""
    return {
        "status": "healthy",
        "service": "extract",
        "message": "Extract endpoint is operational"
    }