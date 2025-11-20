"""
CelesteOS Ingestion API
Handles file uploads from local agent
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys

from config import settings
from router.ingest import router as ingest_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="CelesteOS Ingestion API",
    description="Document ingestion service for CelesteOS",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ingest_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "CelesteOS Ingestion API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ingestion-api",
        "version": "1.0.0"
    }


@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info("CelesteOS Ingestion API starting up...")
    logger.info(f"Upload temp dir: {settings.upload_temp_dir}")
    logger.info(f"Max file size: {settings.max_file_size} bytes")
    logger.info(f"Max chunk size: {settings.max_chunk_size} bytes")
    logger.info("Startup complete!")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info("CelesteOS Ingestion API shutting down...")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
