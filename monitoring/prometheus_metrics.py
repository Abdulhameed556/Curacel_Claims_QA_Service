"""
Prometheus metrics for monitoring and observability.
"""

import time
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter, Response

# ========================
# Metric Definitions
# ========================

# Requests
REQUEST_COUNTER = Counter(
    "requests_total", "Total requests", ["method", "endpoint"]
)

REQUEST_DURATION = Histogram(
    "request_duration_seconds", "Request duration in seconds", ["method", "endpoint"]
)

ERROR_COUNTER = Counter(
    "errors_total", "Total errors", ["method", "endpoint", "error_type"]
)

# Business metrics
DOCUMENTS_PROCESSED = Counter(
    "documents_processed_total", "Total number of documents processed"
)

DOCUMENTS_IN_STORAGE = Gauge(
    "documents_in_storage", "Number of documents currently in storage"
)

OCR_DURATION = Histogram(
    "ocr_processing_duration_seconds", "OCR processing time in seconds"
)

EXTRACTION_DURATION = Histogram(
    "extraction_processing_duration_seconds", "Extraction processing time in seconds"
)

# ========================
# Middleware for request tracking
# ========================

class MetricsMiddleware:
    """Middleware to automatically track request metrics."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            start_time = time.time()

            path = scope.get("path", "unknown")
            method = scope.get("method", "unknown")

            # Normalize path (remove IDs, etc.)
            endpoint = self._normalize_path(path)

            # Increment request counter
            REQUEST_COUNTER.labels(method=method, endpoint=endpoint).inc()

            try:
                await self.app(scope, receive, send)
                duration = time.time() - start_time
                REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
            except Exception as e:
                duration = time.time() - start_time
                REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
                ERROR_COUNTER.labels(method=method, endpoint=endpoint, error_type=type(e).__name__).inc()
                raise
        else:
            await self.app(scope, receive, send)

    def _normalize_path(self, path: str) -> str:
        """Normalize path for metrics (remove variable parts)."""
        if path.startswith("/extract"):
            return "extract"
        elif path.startswith("/ask"):
            return "ask"
        elif path.startswith("/health"):
            return "health"
        elif path == "/":
            return "root"
        else:
            return "unknown"


# ========================
# FastAPI router for Prometheus scraping
# ========================

router = APIRouter(tags=["metrics"])

@router.get("/metrics")
def metrics():
    """Expose metrics in Prometheus format."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
