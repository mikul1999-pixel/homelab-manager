from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from homelab.api.routes import containers, snapshots, updates, health

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Homelab Manager API",
    description="Docker container version management and monitoring API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  #  dev server
        "http://localhost:5173",  # Vite dev server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )

# Include routers
app.include_router(containers.router, prefix="/api/containers", tags=["containers"])
app.include_router(snapshots.router, prefix="/api/snapshots", tags=["snapshots"])
app.include_router(updates.router, prefix="/api/updates", tags=["updates"])
app.include_router(health.router, prefix="/api", tags=["health"])

# Root endpoint
@app.get("/")
def root():
    """API root - health check"""
    return {
        "name": "Homelab Manager API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

# Startup/shutdown events
@app.on_event("startup")
async def startup_event():
    logger.info("Starting Homelab Manager API")
    # Initialize database connection, etc.

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Homelab Manager API")
    # Cleanup resources