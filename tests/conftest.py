"""
Pytest configuration and fixtures for Curacel Claims QA Service tests.
"""

import pytest
from fastapi.testclient import TestClient
from io import BytesIO
from PIL import Image

from src.api.main import app
from src.services.storage_service import clear_all_claims, store_claim
from src.utils.helpers import generate_document_id


@pytest.fixture(scope="session")
def client():
    """Reusable FastAPI test client for the whole test session."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function", autouse=True)
def clean_storage():
    """Ensure storage is clean before and after each test."""
    clear_all_claims()
    yield
    clear_all_claims()


@pytest.fixture
def sample_image_bytes():
    """Create a sample JPEG image for testing uploads."""
    image = Image.new("RGB", (100, 100), color="white")
    image_bytes = BytesIO()
    image.save(image_bytes, format="JPEG")
    image_bytes.seek(0)
    return image_bytes.getvalue()


@pytest.fixture
def invalid_file_bytes():
    """Create an invalid file pretending to be an image."""
    return b"This is not a valid image file"


@pytest.fixture
def sample_claim_data():
    """Provide sample claim data for testing storage and QA."""
    return {
        "patient": {"name": "John Doe", "age": 30},
        "diagnoses": ["Fever", "Headache"],
        "medications": [
            {"name": "Paracetamol", "dosage": "500mg", "quantity": "10 tablets"},
            {"name": "Ibuprofen", "dosage": "200mg", "quantity": "8 tablets"},
        ],
        "procedures": ["Blood test", "Physical examination"],
        "admission": {
            "was_admitted": True,
            "admission_date": "2023-06-10",
            "discharge_date": "2023-06-12",
        },
        "total_amount": "₦25,000",
    }


@pytest.fixture
def sample_stored_claim(sample_claim_data):
    """Store sample claim data in memory and return document_id."""
    doc_id = generate_document_id()
    store_claim(doc_id, sample_claim_data)
    return doc_id
