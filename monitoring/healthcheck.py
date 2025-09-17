"""
Health check endpoints for monitoring and observability.
"""

from fastapi import APIRouter
from typing import Dict, Any
from datetime import datetime
import psutil
import time

from src.services.storage_service import get_storage_stats
from src.core.config import settings
from monitoring.prometheus_metrics import DOCUMENTS_IN_STORAGE  # <-- new

router = APIRouter(prefix="/health", tags=["health"])

# Record service start time for uptime calculation
START_TIME = time.time()


@router.get("")
async def health_check() -> Dict[str, Any]:
    """
    Main health check endpoint.
    Returns overall service health status.
    """
    uptime_seconds = int(time.time() - START_TIME)

    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.version,
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": uptime_seconds,
        "environment": "development" if settings.debug else "production"
    }


@router.get("/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check with system metrics.
    """
    # System metrics
    cpu_percent = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.version,
        "timestamp": datetime.utcnow().isoformat(),
        "system": {
            "cpu_usage_percent": cpu_percent,
            "memory_usage_percent": memory.percent,
            "memory_available_mb": memory.available / (1024 * 1024),
            "disk_usage_percent": disk.percent,
            "disk_free_gb": disk.free / (1024 * 1024 * 1024),
        },
        "configuration": {
            "debug_mode": settings.debug,
            "log_level": settings.log_level,
            "gemini_api_configured": bool(settings.gemini_api_key),
            "ocr_mode": "gemini_vision" if settings.gemini_api_key else "demo_fallback",
        },
    }


@router.get("/storage")
async def storage_health_check() -> Dict[str, Any]:
    """
    Storage-specific health check and statistics.
    Updates Prometheus gauge for documents in storage.
    """
    storage_stats = get_storage_stats()
    documents_count = storage_stats.get("documents_stored", 0)

    # Update Prometheus gauge
    DOCUMENTS_IN_STORAGE.set(documents_count)

    return {
        "status": "healthy",
        "service": "storage",
        "timestamp": datetime.utcnow().isoformat(),
        "storage_type": "in_memory",
        "statistics": storage_stats,
    }


@router.get("/readiness")
async def readiness_check() -> Dict[str, Any]:
    """
    Kubernetes readiness probe endpoint.
    """
    checks = {
        "storage": True,           # In-memory storage is always ready
        "ocr_service": True,       # OCR service stubbed as ready
        "extraction_service": True # Extraction always ready
    }

    all_ready = all(checks.values())

    return {
        "ready": all_ready,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/liveness")
async def liveness_check() -> Dict[str, Any]:
    """
    Kubernetes liveness probe endpoint.
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat(),
    }
