
"""
OCR service using Gemini Vision API for medical claim document processing.
"""

import requests
from PIL import Image
from io import BytesIO
import base64
import time
from typing import Optional
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from monitoring.prometheus_metrics import OCR_DURATION

from src.core.config import settings
from src.core.exceptions import OCRError, GeminiAPIError
from src.core.logging_config import get_logger
from src.utils.helpers import validate_image_format, convert_image_to_base64, convert_pdf_to_image, extract_pdf_text

logger = get_logger(__name__)


def ocr_image(file_bytes: bytes, filename: str) -> tuple[str, str]:
    """
    Extract text from image using Gemini Vision API or fallback method.
    
    Args:
        file_bytes: Raw image/PDF bytes
        filename: Original filename for context
        
    Returns:
        Tuple of (extracted_text, ocr_mode_used)
        
    Raises:
        OCRError: If OCR processing fails
    """
    logger.info(f"Starting OCR processing for file: {filename}")
    
    # Track OCR processing time
    start_time = time.time()
    
    try:
        # Validate file format first
        if not validate_image_format(file_bytes, filename):
            logger.warning(f"Invalid file format for: {filename}")
            raise OCRError(f"Unsupported or corrupted file format: {filename}")
        
        # Handle PDF files
        processing_bytes = file_bytes
        file_type = "image/jpeg"  # Default
        
        if filename.lower().endswith('.pdf'):
            logger.info(f"Processing PDF {filename} directly with Gemini Vision API")
            # For PDFs, we'll pass them directly to Gemini if available
            # Only convert to synthetic image as last resort
            file_type = "application/pdf"
        
        # Try Gemini Vision API if API key is available
        ocr_mode = "demo_fallback"  # Default mode
        if settings.gemini_api_key and settings.gemini_api_key.strip():
            try:
                logger.info("Using Gemini Vision API for OCR")
                result = _gemini_vision_ocr(processing_bytes, filename, file_type)
                ocr_mode = "gemini_vision"
            except (GeminiAPIError, requests.RequestException) as e:
                logger.warning(f"Gemini API failed ({str(e)}), falling back to PDF text extraction or demo OCR")
                # For PDFs, try direct text extraction first
                if filename.lower().endswith('.pdf'):
                    try:
                        logger.info("Attempting direct PDF text extraction")
                        result = extract_pdf_text(file_bytes)
                        ocr_mode = "pdf_text_extraction"
                    except Exception as pdf_error:
                        logger.warning(f"PDF text extraction failed ({pdf_error}), using synthetic image")
                        processing_bytes = convert_pdf_to_image(file_bytes)
                        result = _fallback_ocr(processing_bytes, filename)
                        ocr_mode = "demo_fallback"
                else:
                    result = _fallback_ocr(processing_bytes, filename)
                    ocr_mode = "demo_fallback"
        else:
            logger.info("No Gemini API key configured, trying direct PDF extraction or demo OCR")
            # For PDFs, try direct text extraction first
            if filename.lower().endswith('.pdf'):
                try:
                    logger.info("Attempting direct PDF text extraction")
                    result = extract_pdf_text(file_bytes)
                    ocr_mode = "pdf_text_extraction"
                except Exception as pdf_error:
                    logger.warning(f"PDF text extraction failed ({pdf_error}), using synthetic image")
                    processing_bytes = convert_pdf_to_image(file_bytes)
                    result = _fallback_ocr(processing_bytes, filename)
                    ocr_mode = "demo_fallback"
            else:
                result = _fallback_ocr(processing_bytes, filename)
                ocr_mode = "demo_fallback"
        
        # Record OCR processing time
        duration = time.time() - start_time
        OCR_DURATION.observe(duration)
        logger.info(f"OCR completed in {duration:.2f} seconds using {ocr_mode}")
        
        return result, ocr_mode
            
    except Exception as e:
        # Still record the time even for failed processing
        duration = time.time() - start_time
        OCR_DURATION.observe(duration)
        logger.error(f"OCR processing failed for {filename}: {str(e)}")
        raise OCRError(f"OCR failed for {filename}: {str(e)}")


def _gemini_vision_ocr(file_bytes: bytes, filename: str, file_type: str = "image/jpeg") -> str:
    """
    Use Gemini Vision API to extract text from medical claim documents.
    """
    try:
        # Convert image to base64 for API call
        base64_image = convert_image_to_base64(file_bytes)
        
        # Gemini Vision API endpoint (updated to use gemini-1.5-flash for vision tasks)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.gemini_api_key}"
        
        # Specialized prompt for medical claims
        prompt = """
        Analyze this medical claim document and extract all visible text.
        Pay special attention to:
        - Patient information (name, age, ID)
        - Diagnosis details
        - Medications (names, dosages, quantities)
        - Procedures performed
        - Admission/discharge dates
        - Total amounts and costs
        - Doctor/facility information
        
        Return the complete text content as clearly as possible.
        """
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": file_type,
                            "data": base64_image
                        }
                    }
                ]
            }]
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                text_content = result['candidates'][0]['content']['parts'][0]['text']
                logger.info(f"Gemini Vision API successful for {filename}")
                return text_content
            else:
                raise GeminiAPIError("No text extracted from Gemini Vision API")
        else:
            logger.error(f"Gemini API error: {response.status_code} - {response.text}")
            raise GeminiAPIError(f"Gemini API request failed: {response.status_code}")
            
    except requests.RequestException as e:
        logger.error(f"Gemini API request failed: {str(e)}")
        raise GeminiAPIError(f"Failed to call Gemini Vision API: {str(e)}")


def _fallback_ocr(file_bytes: bytes, filename: str) -> str:
    """
    Fallback OCR method when Gemini Vision API is not available.
    Returns a realistic sample for demonstration purposes.
    """
    logger.info("Using fallback OCR method")
    
    # Validate that we can open the image
    try:
        image = Image.open(BytesIO(file_bytes))
        logger.info(f"Successfully opened image with size: {image.size}")
        
        # For demo purposes, return a realistic medical claim text
        # In a real implementation, you might use Tesseract or another OCR library
        sample_text = """
        MEDICAL CLAIM FORM
        
        Patient Information:
        Name: Jane Doe
        Age: 34
        ID: PAT001234
        
        Diagnosis: Malaria
        
        Medications Prescribed:
        - Paracetamol 500mg - Quantity: 10 tablets
        - Artemether/Lumefantrine - Quantity: 6 tablets
        
        Procedures:
        - Malaria Rapid Test
        - Blood Test
        
        Admission Details:
        Admitted: Yes
        Admission Date: 10/06/2023
        Discharge Date: 12/06/2023
        
        Total Amount: ₦15,000
        
        Doctor: Dr. Smith
        Facility: Lagos General Hospital
        """
        
        return sample_text.strip()
        
    except Exception as e:
        raise OCRError(f"Fallback OCR failed: {str(e)}")


def test_gemini_connection() -> bool:
    """Test if Gemini Vision API is accessible with current configuration."""
    if not settings.gemini_api_key:
        return False
    
    try:
        # Simple test with a minimal request
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key={settings.gemini_api_key}"
        response = requests.get(url.replace(":generateContent", ""), timeout=10)
        return response.status_code in [200, 404]  # 404 is expected for this test endpoint
    except Exception:
        return False