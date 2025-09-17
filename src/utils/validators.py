"""
Input validation utilities for the Curacel Claims QA Service.
"""

import os
import uuid
from fastapi import UploadFile
from src.core.exceptions import ValidationError
from src.core.logging_config import get_logger

logger = get_logger(__name__)


def validate_upload_file(file: UploadFile) -> None:
    """
    Validate uploaded file for extract endpoint.
    
    Args:
        file: FastAPI UploadFile object
        
    Raises:
        ValidationError: If file is invalid
    """
    if not file:
        raise ValidationError("No file provided")
    
    if not file.filename:
        raise ValidationError("File must have a filename")
    
    # Allowed extensions
    allowed_extensions = {".jpg", ".jpeg", ".png", ".pdf", ".bmp", ".tiff", ".tif"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        logger.warning(f"Unsupported file format attempted: {file_ext}")
        raise ValidationError(
            f"Unsupported file format '{file_ext}'. Allowed: {', '.join(sorted(allowed_extensions))}"
        )
    
    # Size validation should happen after file.read() in the route handler
    # because UploadFile doesn't expose .size reliably.


def validate_document_id(document_id: str) -> None:
    """
    Validate document ID format (UUID expected).
    
    Args:
        document_id: Document ID to validate
        
    Raises:
        ValidationError: If document ID is invalid
    """
    if not document_id or not isinstance(document_id, str):
        raise ValidationError("Document ID must be a non-empty string")
    
    try:
        uuid.UUID(document_id)
    except ValueError:
        raise ValidationError("Document ID must be a valid UUID")


def validate_question(question: str) -> None:
    """
    Validate question input (though it will be overridden internally).
    
    Args:
        question: Question string to validate
        
    Raises:
        ValidationError: If question is invalid
    """
    if not question or not isinstance(question, str) or not question.strip():
        raise ValidationError("Question must be a non-empty string")
