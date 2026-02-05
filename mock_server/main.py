"""
Energy Trading Connectivity Monitor - Mock Server
==================================================
FastAPI application that simulates the CKW energy API with OAuth2 protection.
Serves real data from the CKW specification examples.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mock_server.routers import energy, plant, control, health
from mock_server.auth import oauth2


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Runs on startup and shutdown.
    """
    # Startup
    print("🚀 Starting Energy Trading Mock Server...")
    print(f"📅 Server time: {datetime.now(timezone.utc).isoformat()}")
    yield
    # Shutdown
    print("👋 Shutting down Energy Trading Mock Server...")


# Create FastAPI application
app = FastAPI(
    title="Energy Trading API (Mock)",
    description="""
    ## Mock API for Energy Trading Connectivity Monitor
    
    This API simulates the CKW (Centralschweizerische Kraftwerke) public data API.
    It provides endpoints for:
    
    - **Energy Prices**: Dynamic quarter-hourly pricing data
    - **Plant Status**: Real-time power plant telemetry
    - **Control Signals**: TRA demand-side management signals
    
    ### Authentication
    
    All data endpoints require OAuth2 Bearer token authentication.
    Use the `/oauth/token` endpoint to obtain an access token.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(oauth2.router, prefix="/oauth", tags=["Authentication"])
app.include_router(energy.router, prefix="/api/v1/energy", tags=["Energy Prices"])
app.include_router(plant.router, prefix="/api/v1/plant", tags=["Power Plant"])
app.include_router(control.router, prefix="/api/v1/control", tags=["Control Signals"])
app.include_router(health.router, tags=["Health"])


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - redirects to docs."""
    return {
        "message": "Energy Trading Mock API",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
