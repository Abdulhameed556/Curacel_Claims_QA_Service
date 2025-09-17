# Test Documents

This folder contains sample claim documents for testing the Curacel Claims QA Service.

## Supported Formats
- PDF files (.pdf)
- Image files (.png, .jpg, .jpeg)

## Usage
1. Place your test documents in this folder
2. Run `python test_service.py` to test with these documents
3. The test script will automatically detect and use available files

## Example Files
- Place your EXAMPLE_IMAGE_1 and EXAMPLE_IMAGE_2 PDFs here
- Any additional claim documents for testing

## Notes
- PDFs will be converted to images for OCR processing
- The service supports both Gemini Vision API and demo mode
- Test results will show which OCR mode was used
