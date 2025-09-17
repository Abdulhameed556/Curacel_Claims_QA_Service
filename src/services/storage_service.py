
"""
In-memory storage service for claim data.
In production, this would be replaced with a proper database.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import threading
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from monitoring.prometheus_metrics import DOCUMENTS_PROCESSED, DOCUMENTS_IN_STORAGE

from src.core.logging_config import get_logger
from src.core.exceptions import DocumentNotFoundError

logger = get_logger(__name__)

# Thread-safe in-memory storage
_CLAIM_STORE: Dict[str, Dict[str, Any]] = {}
_STORAGE_LOCK = threading.Lock()


def store_claim(document_id: str, claim_data: Dict[str, Any]) -> None:
    """Store claim data in memory with metadata."""
    with _STORAGE_LOCK:
        enriched_data = {
            **claim_data,
            "_metadata": {
                "document_id": document_id,
                "created_at": datetime.utcnow().isoformat(),
                "last_accessed": datetime.utcnow().isoformat(),
                "access_count": 0
            }
        }
        _CLAIM_STORE[document_id] = enriched_data
        
        # Update metrics
        DOCUMENTS_PROCESSED.inc()
        DOCUMENTS_IN_STORAGE.set(len(_CLAIM_STORE))
        
        logger.info(f"Stored claim data for document_id: {document_id}")


def get_claim(document_id: str) -> Dict[str, Any]:
    """Retrieve claim data by document ID."""
    with _STORAGE_LOCK:
        claim_data = _CLAIM_STORE.get(document_id)
        if not claim_data:
            logger.warning(f"Document not found: {document_id}")
            raise DocumentNotFoundError(f"Document with ID '{document_id}' not found")
        
        # Update metadata
        claim_data["_metadata"]["last_accessed"] = datetime.utcnow().isoformat()
        claim_data["_metadata"]["access_count"] += 1
        
        logger.info(f"Retrieved claim data for document_id: {document_id}")
        return claim_data


def delete_claim(document_id: str) -> bool:
    """Delete claim data by document ID."""
    with _STORAGE_LOCK:
        if document_id in _CLAIM_STORE:
            del _CLAIM_STORE[document_id]
            DOCUMENTS_IN_STORAGE.set(len(_CLAIM_STORE))  # keep metrics accurate
            logger.info(f"Deleted claim data for document_id: {document_id}")
            return True
        else:
            logger.warning(f"Cannot delete, document not found: {document_id}")
            return False


def list_all_claims() -> List[str]:
    """Get list of all stored document IDs."""
    with _STORAGE_LOCK:
        return list(_CLAIM_STORE.keys())


def get_storage_stats() -> Dict[str, Any]:
    """Get storage statistics for monitoring."""
    with _STORAGE_LOCK:
        total_documents = len(_CLAIM_STORE)
        if total_documents == 0:
            return {
                "total_documents": 0,
                "oldest_document": None,
                "newest_document": None,
                "total_access_count": 0,
                "avg_access_count": 0
            }
        
        access_counts = []
        creation_times = []
        for claim_data in _CLAIM_STORE.values():
            metadata = claim_data.get("_metadata", {})
            access_counts.append(metadata.get("access_count", 0))
            created_at = metadata.get("created_at")
            if created_at:
                creation_times.append(created_at)
        
        return {
            "total_documents": total_documents,
            "oldest_document": min(creation_times) if creation_times else None,
            "newest_document": max(creation_times) if creation_times else None,
            "total_access_count": sum(access_counts),
            "avg_access_count": sum(access_counts) / len(access_counts) if access_counts else 0
        }


def clear_all_claims() -> int:
    """Clear all stored claims (useful for testing)."""
    with _STORAGE_LOCK:
        count = len(_CLAIM_STORE)
        _CLAIM_STORE.clear()
        DOCUMENTS_IN_STORAGE.set(0)  # reset metric
        logger.warning(f"Cleared all claim data ({count} documents)")
        return count


def document_exists(document_id: str) -> bool:
    """Check if a document exists in storage."""
    with _STORAGE_LOCK:
        return document_id in _CLAIM_STORE