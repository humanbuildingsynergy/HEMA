# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# api/main.py
"""FastAPI application entry point for the energy analysis API."""
import warnings

# Suppress protobuf/grpc warnings (known issue with Google libraries)
warnings.filterwarnings("ignore", message=".*GetPrototype.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="google")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import chat_router, session_router, data_router
from utils.logger import setup_logger

logger = setup_logger()

# Create FastAPI application
app = FastAPI(
    title="Energy Analysis API",
    description="API for LLM-based Home Energy Management Assistant (HEMA)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint (available at both / and /api for convenience)
@app.get("/health", tags=["health"])
@app.get("/api/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "energy-analysis-api"}


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Energy Analysis API",
        "version": "1.0.0",
        "description": "LLM-based Home Energy Management Assistant",
        "docs": "/docs",
        "health": "/health",
    }


# Include routers with /api prefix
app.include_router(chat_router, prefix="/api")
app.include_router(session_router, prefix="/api")
app.include_router(data_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("Energy Analysis API starting up...")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Energy Analysis API shutting down...")
