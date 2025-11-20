"""
CelesteOS Cloud API - Main Application
FastAPI REST API for CelesteOS cloud backend

Worker 3 — Cloud API Carpenter
Scaffolds all cloud API endpoints, middleware, routing structure
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.supabase import supabase_client
from app.api.v1 import api_router
from app.core.exceptions import CelesteAPIException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting CelesteOS Cloud API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"API Version: {settings.API_VERSION}")

    # Test Supabase connection
    try:
        supabase_client.health_check()
        logger.info("✓ Supabase connection established")
    except Exception as e:
        logger.error(f"✗ Supabase connection failed: {e}")

    yield

    # Shutdown
    logger.info("Shutting down CelesteOS Cloud API...")


# Create FastAPI application
app = FastAPI(
    title="CelesteOS Cloud API",
    description="REST API for CelesteOS yacht management system",
    version=settings.API_VERSION,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler for CelesteAPIException
@app.exception_handler(CelesteAPIException)
async def celeste_exception_handler(request: Request, exc: CelesteAPIException):
    """Handle CelesteOS API exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )


# Global exception handler for unexpected errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": str(exc) if settings.ENVIRONMENT == "development" else None
            }
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "CelesteOS Cloud API",
        "version": settings.API_VERSION,
        "docs": "/docs" if settings.ENVIRONMENT == "development" else "disabled"
    }


# Include API router
app.include_router(
    api_router,
    prefix=f"/{settings.API_VERSION}"
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level="info"
    )
