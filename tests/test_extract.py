"""
Tests for the /extract endpoint.
"""

import pytest
from fastapi import status
from io import BytesIO


def _upload_file(client, filename: str, content: bytes, mime: str = "image/jpeg"):
    """Helper to upload a file to the /extract endpoint."""
    return client.post(
        "/extract",
        files={"file": (filename, BytesIO(content), mime)}
    )


def test_extract_success(client, clean_storage, sample_image_bytes):
    """Test successful document extraction with enriched metadata."""
    response = _upload_file(client, "test_claim.jpg", sample_image_bytes)
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()

    # Check required fields
    for field in ["document_id", "patient", "medications", "diagnoses",
                  "procedures", "admission", "total_amount"]:
        assert field in data, f"Missing field in response: {field}"

    # Metadata checks (from storage enrichment)
    assert "_metadata" in data, "Response missing _metadata"
    assert "created_at" in data["_metadata"]
    assert "document_id" in data["_metadata"]

    # Patient structure
    assert "name" in data["patient"]
    assert "age" in data["patient"]

    # Medications structure
    assert isinstance(data["medications"], list)
    if data["medications"]:
        med = data["medications"][0]
        for key in ["name", "dosage", "quantity"]:
            assert key in med, f"Medication missing key: {key}"


def test_extract_no_file(client):
    """Test extract with no file provided."""
    response = client.post("/extract")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.text


def test_extract_empty_file(client):
    """Test extract with empty file."""
    response = _upload_file(client, "empty.jpg", b"")
    assert response.status_code in [status.HTTP_400_BAD_REQUEST,
                                    status.HTTP_422_UNPROCESSABLE_ENTITY], response.text


def test_extract_invalid_format(client):
    """Test extract with unsupported file format."""
    response = _upload_file(client, "test.txt", b"not an image", mime="text/plain")
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text


def test_extract_health_endpoint(client):
    """Test extract health check endpoint."""
    response = client.get("/extract/health")
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "extract"


def test_extract_pdf_file(client, clean_storage):
    """Test extract with PDF file (simulated)."""
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<<\n/Size 1\n/Root 1 0 R\n>>\nstartxref\n9\n%%EOF"

    response = _upload_file(client, "test_claim.pdf", pdf_bytes, mime="application/pdf")

    # PDF support depends on OCR backend: expect either success or validation error
    assert response.status_code in [status.HTTP_200_OK,
                                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    status.HTTP_400_BAD_REQUEST], response.text


def test_multiple_extractions(client, clean_storage, sample_image_bytes):
    """Test multiple document extractions and uniqueness of IDs."""
    response1 = _upload_file(client, "claim1.jpg", sample_image_bytes)
    assert response1.status_code == status.HTTP_200_OK, response1.text
    doc_id1 = response1.json()["document_id"]

    response2 = _upload_file(client, "claim2.jpg", sample_image_bytes)
    assert response2.status_code == status.HTTP_200_OK, response2.text
    doc_id2 = response2.json()["document_id"]

    assert doc_id1 != doc_id2, "Document IDs should be unique"
