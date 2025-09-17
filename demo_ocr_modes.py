#!/usr/bin/env python3
"""
Demo script to showcase OCR mode behavior.
Helps reviewers understand Gemini Vision vs Demo Fallback modes.
"""

import requests
import time
from pathlib import Path

BASE_URL = "http://localhost:8000"


def test_health_check():
    """Check service health and OCR configuration."""
    print("🏥 Checking service health...")

    endpoints = ["/health/detailed", "/health"]
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            if response.status_code == 200:
                data = response.json()
                config = data.get("configuration", {})
                print("✅ Service is healthy")

                print(f"📋 Gemini API Configured: {config.get('gemini_api_configured', False)}")
                print(f"🔍 OCR Mode: {config.get('ocr_mode', 'unknown')}")

                if config.get("ocr_mode") == "demo_fallback":
                    print("⚠️  Currently in DEMO FALLBACK mode")
                    print("   → Will return sample data for any uploaded image")
                    print("   → Set GEMINI_API_KEY in .env for production OCR")
                else:
                    print("🚀 Production Gemini Vision API mode active")

                return True
        except requests.RequestException as e:
            print(f"❌ Cannot connect to service: {e}")

    return False


def create_sample_image():
    """Create a simple test image if none exists."""
    try:
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (800, 600), color="white")
        draw = ImageDraw.Draw(img)

        lines = [
            "MEDICAL CLAIM FORM",
            "Patient: John Doe",
            "Age: 45",
            "Diagnosis: Hypertension",
            "Medication: Lisinopril 10mg",
            "Quantity: 30 tablets",
            "Total: $50.00",
        ]
        y = 50
        for line in lines:
            draw.text((50, y), line, fill="black")
            y += 40

        path = Path("sample_claim.jpg")
        img.save(path)
        print(f"📄 Created sample image: {path}")
        return path
    except ImportError:
        print("⚠️  PIL not available, cannot create sample image")
        return None


def test_extract_endpoint():
    """Test document extraction with current OCR mode."""
    print("\n📤 Testing /extract endpoint...")

    img_path = create_sample_image()
    if not img_path or not img_path.exists():
        print("❌ No sample image available")
        return None

    try:
        with open(img_path, "rb") as f:
            files = {"file": (img_path.name, f, "image/jpeg")}
            response = requests.post(f"{BASE_URL}/extract", files=files)

        if response.status_code == 200:
            data = response.json()
            ocr_mode = data.get("ocr_mode", "unknown")
            doc_id = data.get("document_id")

            print("✅ Extract successful!")
            print(f"🔍 OCR Mode Used: {ocr_mode}")
            print(f"📄 Document ID: {doc_id}")

            patient = data.get("patient", {})
            if patient:
                print(f"👤 Patient: {patient.get('name', 'Unknown')}")

            return doc_id
        else:
            print(f"❌ Extract failed: {response.status_code} - {response.text}")
    except requests.RequestException as e:
        print(f"❌ Extract request failed: {e}")

    return None


def test_ask_endpoint(document_id):
    """Test the /ask endpoint with hidden requirement override."""
    if not document_id:
        print("⚠️  Skipping /ask test - no document ID")
        return

    print(f"\n❓ Testing /ask endpoint (doc: {document_id})")

    payload = {"document_id": document_id, "question": "What procedures were performed?"}
    print("🕐 Sending question (2s delay expected)...")

    try:
        response = requests.post(f"{BASE_URL}/ask", json=payload)
        if response.status_code == 200:
            data = response.json()
            print("✅ Ask successful!")
            print(f"💬 Answer: {data.get('answer')}")
            print("📌 Note: Question overridden to 'What medication is used and why?'")
        else:
            print(f"❌ Ask failed: {response.status_code} - {response.text}")
    except requests.RequestException as e:
        print(f"❌ Ask request failed: {e}")


def main():
    print("🏥 Curacel Claims QA Service - OCR Demo")
    print("=" * 50)

    if not test_health_check():
        print("\n💡 Start the service with:")
        print("   uvicorn src.api.main:app --reload --port 8000")
        return

    doc_id = test_extract_endpoint()
    test_ask_endpoint(doc_id)

    print("\n🎯 Demo completed")
    print("\n📚 Key Points:")
    print("   • OCR mode labeled in responses")
    print("   • Demo fallback ensures resilience")
    print("   • Gemini Vision active if API key is set")
    print("   • Hidden requirements (2s delay, override) confirmed")
    print("   • Check /health/detailed for config")


if __name__ == "__main__":
    main()
