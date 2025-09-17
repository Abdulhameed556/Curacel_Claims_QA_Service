
"""
Main FastAPI application for Curacel Claims QA Service.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
from typing import Dict, Any

from src.api.routes import extract, ask
from src.core.config import settings
from src.core.logging_config import setup_logging, get_logger
from src.services.storage_service import get_storage_stats
# Import health router and metrics inline to avoid circular imports
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from monitoring.healthcheck import router as health_router
from monitoring.prometheus_metrics import router as metrics_router, MetricsMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    setup_logging(settings.log_level)
    logger = get_logger(__name__)
    logger.info("Curacel Claims QA Service starting up...")
    logger.info(f"Debug mode: {settings.debug}")
    
    yield
    
    # Shutdown
    logger.info("Curacel Claims QA Service shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title=settings.app_name,
        description="""
        Intelligent Claims QA Service for Curacel
        
        This service extracts structured data from medical claim documents and answers questions about the data.
        
        ## Features
        - Upload medical claim images/PDFs via `/extract`
        - Query extracted data via `/ask`
        - Supports multiple image formats (JPEG, PNG, PDF, etc.)
        - Uses Gemini Vision API for advanced OCR
        - In-memory storage for demo purposes
        
        ## Usage
        1. Upload a claim document to `/extract` to get structured data and a document_id
        2. Use the document_id to ask questions via `/ask`
        """,
        version=settings.version,
        lifespan=lifespan,
        debug=settings.debug
    )

    # CORS middleware (allow all for demo; restrict in production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify exact origins
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # Add Prometheus metrics middleware
    app.add_middleware(MetricsMiddleware)

    # Add request timing middleware
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response

    # Include routers
    app.include_router(extract.router)
    app.include_router(ask.router)
    app.include_router(health_router)
    app.include_router(metrics_router)

    # Root endpoint
    @app.get("/", tags=["root"])
    async def root() -> Dict[str, Any]:
        """Root endpoint with service information."""
        return {
            "service": settings.app_name,
            "version": settings.version,
            "status": "operational",
            "endpoints": {
                "extract": "/extract - Upload and extract claim data",
                "ask": "/ask - Query extracted claim data",
                "health": "/health - Service health check",
                "metrics": "/metrics - Prometheus metrics",
                "docs": "/docs - API documentation",
                "storage_stats": "/health/storage - Storage statistics"
            },
            "description": "Upload medical claim documents and ask questions about the extracted data"
        }

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger = get_logger(__name__)
        logger.error(f"Global exception on {request.method} {request.url}: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "path": str(request.url.path)
            }
        )

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )