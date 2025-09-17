"""
Tests for the /ask endpoint.
"""

import pytest
import time
from fastapi import status


def ask_question(client, document_id, question):
    """Helper function to make ask requests."""
    return client.post("/ask", json={"document_id": document_id, "question": question})


def test_ask_success(client, sample_stored_claim, monkeypatch):
    """Test successful question answering with mocked sleep."""
    monkeypatch.setattr(time, "sleep", lambda x: None)  # mock delay

    response = ask_question(client, sample_stored_claim, "What is the patient's name?")
    assert response.status_code == 200
    answer = response.json()["answer"].lower()
    assert any(k in answer for k in ["paracetamol", "medication", "prescribed"]), f"Unexpected answer: {answer}"


def test_ask_with_timing(client, sample_stored_claim):
    """Test that the 2-second delay is applied when not mocked."""
    start_time = time.time()
    response = ask_question(client, sample_stored_claim, "What medication was prescribed?")
    duration = time.time() - start_time
    
    assert response.status_code == 200
    assert duration >= 2.0, "Expected 2-second delay not applied"


def test_ask_document_not_found(client):
    """Test asking about non-existent document."""
    response = ask_question(client, "nonexistent-id", "What medication was prescribed?")
    assert response.status_code == 404


def test_ask_invalid_document_id(client):
    """Test with invalid document ID format."""
    response = ask_question(client, "", "What medication was prescribed?")
    assert response.status_code == 400


def test_ask_empty_question(client, sample_stored_claim):
    """Test with empty question."""
    response = ask_question(client, sample_stored_claim, "")
    assert response.status_code == 400


def test_ask_question_override(client, sample_stored_claim, monkeypatch):
    """Test that questions are always overridden to medication question."""
    monkeypatch.setattr(time, "sleep", lambda x: None)  # Speed up tests
    
    questions = [
        "What is the patient's name?",
        "How old is the patient?", 
        "What was the total cost?",
        "When was the patient admitted?",
        "What procedures were performed?"
    ]
    
    for question in questions:
        response = ask_question(client, sample_stored_claim, question)
        assert response.status_code == 200
        answer = response.json()["answer"].lower()
        # All answers should be about medications regardless of the question
        assert any(k in answer for k in ["medication", "paracetamol", "prescribed", "ibuprofen"])


def test_ask_health_endpoint(client):
    """Test ask health check endpoint."""
    response = client.get("/ask/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ask"


def test_ask_multiple_medications(client, monkeypatch):
    """Test asking about claim with multiple medications."""
    monkeypatch.setattr(time, "sleep", lambda x: None)
    
    from src.services.storage_service import store_claim
    from src.utils.helpers import generate_document_id
    
    claim_data = {
        "patient": {"name": "Jane Smith", "age": 45},
        "diagnoses": ["Malaria", "Fever"],
        "medications": [
            {"name": "Paracetamol", "dosage": "500mg", "quantity": "12 tablets"},
            {"name": "Artemether", "dosage": "20mg", "quantity": "6 tablets"},
            {"name": "Lumefantrine", "dosage": "120mg", "quantity": "6 tablets"}
        ],
        "procedures": ["Malaria test"],
        "admission": {"was_admitted": False},
        "total_amount": "₦18,500"
    }
    
    doc_id = generate_document_id()
    store_claim(doc_id, claim_data)
    
    response = ask_question(client, doc_id, "What treatments were given?")
    assert response.status_code == 200
    answer = response.json()["answer"].lower()
    assert any(med in answer for med in ["paracetamol", "artemether", "lumefantrine"])


def test_ask_no_medications(client, monkeypatch):
    """Test asking about claim with no medications."""
    monkeypatch.setattr(time, "sleep", lambda x: None)
    
    from src.services.storage_service import store_claim
    from src.utils.helpers import generate_document_id
    
    claim_data = {
        "patient": {"name": "Bob Johnson", "age": 28},
        "diagnoses": ["Consultation"],
        "medications": [],
        "procedures": ["Physical examination"],
        "admission": {"was_admitted": False},
        "total_amount": "₦5,000"
    }
    
    doc_id = generate_document_id()
    store_claim(doc_id, claim_data)
    
    response = ask_question(client, doc_id, "What medication was prescribed?")
    assert response.status_code == 200
    answer = response.json()["answer"].lower()
    assert "no medication" in answer or "not found" in answer
