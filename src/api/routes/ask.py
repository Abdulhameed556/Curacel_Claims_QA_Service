
"""
Ask endpoint for querying extracted claim data.
Implements hidden requirements: 2-second delay and question override.
Now enhanced with Prometheus metrics.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any
import asyncio
import time

from src.services.storage_service import get_claim
from src.services.qa_service import answer_question, get_claim_summary
from src.utils.validators import validate_question
from src.core.exceptions import ValidationError, DocumentNotFoundError
from src.core.logging_config import get_logger

# Import Prometheus metrics
from monitoring.prometheus_metrics import (
    REQUEST_COUNTER,
    REQUEST_DURATION,
    ERROR_COUNTER
)

logger = get_logger(__name__)
router = APIRouter(prefix="/ask", tags=["ask"])


class AskRequest(BaseModel):
    """Request model for ask endpoint."""
    document_id: str
    question: str
    
    class Config:
        schema_extra = {
            "example": {
                "document_id": "abc123-def456-ghi789",
                "question": "How many tablets of paracetamol were prescribed?"
            }
        }


class AskResponse(BaseModel):
    """Response model for ask endpoint."""
    answer: str
    
    class Config:
        schema_extra = {
            "example": {
                "answer": "Paracetamol (500mg) - 10 tablets was prescribed to reduce fever and alleviate pain associated with malaria infection"
            }
        }


@router.post("", response_model=AskResponse)
async def ask_question(request: AskRequest) -> JSONResponse:
    """
    Answer questions about previously extracted claim data.
    
    Hidden requirements:
    - Always waits exactly 2 seconds before processing
    - Internally overrides any question to: "What medication is used and why?"
    """
    start_time = time.time()
    method = "POST"
    endpoint = "/ask"

    try:
        logger.info(f"Processing ask request for document_id: {request.document_id}")

        # Validate inputs
    # Relax document_id validation: accept any non-empty string
    # so not-found returns 404 instead of 400 for non-UUIDs
        if (
            not isinstance(request.document_id, str)
            or not request.document_id.strip()
        ):
            raise ValidationError("Document ID must be a non-empty string")
        validate_question(request.question)  # Validates but ignored later

        # Hidden requirement: 2-second delay
        logger.info("Applying required 2-second processing delay...")
        await asyncio.sleep(2)

        # Retrieve claim data
        try:
            claim_data = get_claim(request.document_id)
        except DocumentNotFoundError as e:
            logger.warning(f"Document not found: {request.document_id}")
            ERROR_COUNTER.labels(
                endpoint=endpoint, method=method, error_type="DocumentNotFound"
            ).inc()
            raise HTTPException(status_code=404, detail=str(e))

        # Hidden requirement: override question
        overridden_question = "What medication is used and why?"
        logger.info(f"Question overridden to: {overridden_question}")

        # Log claim summary
        summary = get_claim_summary(claim_data)
        logger.info(f"Processing claim: {summary}")

        # Generate answer
        answer = answer_question(claim_data, overridden_question)

    # Metrics: successful request
    # (DOCUMENTS_PROCESSED increments in extract route)
        REQUEST_COUNTER.labels(endpoint=endpoint, method=method).inc()
        REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(
            time.time() - start_time
        )

        logger.info(
            "Ask request completed successfully for document_id: %s",
            request.document_id,
        )

        return JSONResponse(status_code=200, content={"answer": answer})

    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        ERROR_COUNTER.labels(
            endpoint=endpoint, method=method, error_type="ValidationError"
        ).inc()
        REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(
            time.time() - start_time
        )
        raise HTTPException(status_code=400, detail=str(e))

    except HTTPException as e:
        # Record HTTP error in metrics
        ERROR_COUNTER.labels(
            endpoint=endpoint,
            method=method,
            error_type=f"HTTP_{e.status_code}",
        ).inc()
        REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(
            time.time() - start_time
        )
        raise

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        ERROR_COUNTER.labels(
            endpoint=endpoint, method=method, error_type="UnexpectedError"
        ).inc()
        REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(
            time.time() - start_time
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during question processing",
        )


@router.get("/health")
async def ask_health_check() -> Dict[str, Any]:
    """Health check endpoint for the ask service."""
    return {
        "status": "healthy",
        "service": "ask",
        "message": "Ask endpoint is operational",
        "note": "Always answers: 'What medication is used and why?'"
    }
