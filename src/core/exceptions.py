"""
Custom exceptions for the Curacel Claims QA Service.
"""


class CuracelBaseException(Exception):
    """Base exception for all Curacel-specific errors."""
    pass


class OCRError(CuracelBaseException):
    """Raised when OCR processing fails."""
    pass


class ExtractionError(CuracelBaseException):
    """Raised when data extraction fails."""
    pass


class ValidationError(CuracelBaseException):
    """Raised when input validation fails."""
    pass


class DocumentNotFoundError(CuracelBaseException):
    """Raised when a document is not found in storage."""
    pass


class GeminiAPIError(CuracelBaseException):
    """Raised when Gemini Vision API calls fail."""
    pass
