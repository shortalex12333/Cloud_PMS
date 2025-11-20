"""
CelesteOS Predictive Maintenance Engine

This is the main entry point for the predictive maintenance microservice.
It provides risk scoring, anomaly detection, and predictive insights for yacht equipment.

Architecture:
- FastAPI web service
- Supabase/Postgres for data storage
- pgvector for embeddings
- Statistical and rule-based engine (V1 - no ML yet)

Author: CelesteOS Engineering
Version: 1.0
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

from router import risk, insights
from services.utils.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for the application"""
    logger.info("Starting CelesteOS Predictive Maintenance Engine")
    yield
    logger.info("Shutting down CelesteOS Predictive Maintenance Engine")


# Initialize FastAPI app
app = FastAPI(
    title="CelesteOS Predictive Maintenance Engine",
    description="Statistical and rule-based predictive maintenance system for yacht equipment",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "ok",
        "service": "predictive-maintenance-engine",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "CelesteOS Predictive Maintenance Engine",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "risk_state": "/v1/predictive/state",
            "insights": "/v1/predictive/insights",
            "run_manual": "/v1/predictive/run",
            "run_for_yacht": "/v1/predictive/run-for-yacht"
        }
    }


# Include routers
app.include_router(risk.router, prefix="/v1/predictive", tags=["risk"])
app.include_router(insights.router, prefix="/v1/predictive", tags=["insights"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
