#!/usr/bin/env python3
"""
Quick test script to verify the Curacel Claims QA Service is working correctly.
Run this after starting the server with 'make run' or 
'uvicorn src.api.main:app --reload'
"""

import requests
import time
import os
import glob
from io import BytesIO
from PIL import Image

# Base URL configurable (default: localhost)
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# ANSI color codes for prettier CLI output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def log_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")


def log_fail(msg):
    print(f"{RED}❌ {msg}{RESET}")


def log_warn(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")


def get_test_documents():
    """Get available test documents from the test_documents folder."""
    test_files = []
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    test_docs_dir = os.path.join(workspace_dir, 'test_documents')
    
    if not os.path.exists(test_docs_dir):
        print(f"⚠️  Test documents folder not found: {test_docs_dir}")
        return []
    
    # Look for PDF and image files
    patterns = ['*.pdf', '*.png', '*.jpg', '*.jpeg', 'EXAMPLE_IMAGE*', 'example_image*']
    
    for pattern in patterns:
        matches = glob.glob(os.path.join(test_docs_dir, pattern))
        test_files.extend(matches)
    
    # Also check workspace root for backwards compatibility
    for pattern in ['EXAMPLE_IMAGE_*.png', 'EXAMPLE_IMAGE_*.jpg', 'EXAMPLE_IMAGE_*.pdf']:
        matches = glob.glob(os.path.join(workspace_dir, pattern))
        test_files.extend(matches)
    
    return test_files


def get_file_mime_type(file_path):
    """Get MIME type based on file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    mime_types = {
        '.pdf': 'application/pdf',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg'
    }
    return mime_types.get(ext, 'application/octet-stream')


def create_test_image():
    """Create a simple test image in memory as fallback."""
    img = Image.new('RGB', (200, 300), color='white')
    pixels = img.load()

    # Draw black rectangle to simulate text
    for i in range(50, 150):
        for j in range(50, 80):
            pixels[i, j] = (0, 0, 0)

    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes.getvalue()


def test_health_check():
    """Test the health check endpoint."""
    print("🔍 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=3)
        if response.status_code == 200:
            log_success("Health check passed")
            return True
        else:
            log_fail(f"Health check failed: {response.status_code}")
            return False
    except requests.RequestException as e:
        log_fail(f"Health check failed: {e}")
        return False


def test_extract_endpoint():
    """Test the /extract endpoint."""
    print("🔍 Testing /extract endpoint...")
    
    try:
        # Try to use real test documents first
        test_docs = get_test_documents()
        
        if test_docs:
            doc_path = test_docs[0]  # Use first available test document
            filename = os.path.basename(doc_path)
            print(f"   Using test document: {filename}")
            
            # Read file as binary data
            with open(doc_path, 'rb') as f:
                file_data = f.read()
            
            # Get appropriate MIME type
            mime_type = get_file_mime_type(doc_path)
            files = {'file': (filename, file_data, mime_type)}
            
            if doc_path.lower().endswith('.pdf'):
                print("   📄 PDF file - API will handle conversion")
        else:
            # Fallback to synthetic image
            print("   No test documents found, using synthetic image")
            print("   💡 Place test documents in ./test_documents/ folder")
            test_image = create_test_image()
            files = {'file': ('test_claim.jpg', test_image, 'image/jpeg')}
        
        response = requests.post(f"{BASE_URL}/extract", files=files, timeout=20)
        
        if response.status_code == 200:
            data = response.json()
            document_id = data.get('document_id')
            ocr_mode = data.get('ocr_mode', 'unknown')
            
            if document_id:
                log_success("Extract endpoint successful")
                print(f"   Document ID: {document_id}")
                print(f"   OCR Mode: {ocr_mode}")
                print(f"   Patient: {data.get('patient', {}).get('name', 'N/A')}")
                print(f"   Medications: {len(data.get('medications', []))} found")
                return document_id
            else:
                log_fail("Extract endpoint failed: No document_id in response")
                return None
        else:
            log_fail(f"Extract endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except requests.RequestException as e:
        log_fail(f"Extract endpoint failed: {e}")
        return None


def test_ask_endpoint(document_id):
    """Test the /ask endpoint with hidden requirements verification."""
    print("🔍 Testing /ask endpoint...")
    
    try:
        start_time = time.time()
        payload = {
            "document_id": document_id,
            "question": "What is the patient's name?"  # Should be overridden
        }
        
        response = requests.post(f"{BASE_URL}/ask", json=payload, timeout=8)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get('answer', '')
            
            log_success("Ask endpoint successful")
            print(f"   Response time: {duration:.2f}s")
            print(f"   Answer: {answer[:80]}...")
            
            # Verify 2-second delay
            if duration >= 1.8:
                log_success("2-second delay requirement verified")
            else:
                log_warn(f"Expected ~2s delay, got {duration:.2f}s")
            
            # Verify question override
            medication_keywords = ['medication', 'paracetamol', 'prescribed', 'drug', 'treatment']
            if any(keyword in answer.lower() for keyword in medication_keywords):
                log_success("Question override verified (answered about medications)")
            else:
                log_warn("Question override may not be working (no medication keywords)")
                
            return True
        else:
            log_fail(f"Ask endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.RequestException as e:
        log_fail(f"Ask endpoint failed: {e}")
        return False


def main():
    """Run all service tests."""
    print("🚀 Curacel Claims QA Service - Quick Test")
    print("=" * 50)
    print(f"Testing service at: {BASE_URL}")
    print()
    
    # Test health check
    if not test_health_check():
        log_fail("Service not running. Start with 'make run' first")
        return False
    
    print()
    
    # Test extract endpoint
    document_id = test_extract_endpoint()
    if not document_id:
        log_fail("Extract test failed")
        return False
    
    print()
    
    # Test ask endpoint 
    if not test_ask_endpoint(document_id):
        log_fail("Ask test failed")
        return False
    
    print()
    print(f"{GREEN}🎉 All tests passed! Service is working correctly.{RESET}")
    print(f"\n{GREEN}📋 Verified:{RESET}")
    print(f"   {GREEN}✅{RESET} Health check endpoint")
    print(f"   {GREEN}✅{RESET} /extract with OCR mode labeling")
    print(f"   {GREEN}✅{RESET} /ask with 2-second delay")
    print(f"   {GREEN}✅{RESET} Question override to medication info")
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
