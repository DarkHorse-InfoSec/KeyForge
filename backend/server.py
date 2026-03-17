"""KeyForge API — Universal API Infrastructure Assistant (v2.0)"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
import logging
import sys
from pathlib import Path

# Ensure the backend package is importable when running via `uvicorn server:app`
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import client, db
from backend.routes.auth import router as auth_router
from backend.routes.credentials import router as credentials_router
from backend.routes.projects import router as projects_router
from backend.routes.dashboard import router as dashboard_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("keyforge")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern lifespan handler: create indexes on startup, close DB on shutdown."""
    logger.info("KeyForge starting up...")
    await create_indexes()
    yield
    logger.info("KeyForge shutting down...")
    client.close()


async def create_indexes():
    """Create MongoDB indexes for performance."""
    try:
        # Users
        await db.users.create_index("username", unique=True)
        await db.users.create_index("id", unique=True)

        # Credentials
        await db.credentials.create_index("id", unique=True)
        await db.credentials.create_index("user_id")
        await db.credentials.create_index([("user_id", 1), ("api_name", 1)])

        # Project analyses
        await db.project_analyses.create_index("id", unique=True)
        await db.project_analyses.create_index("user_id")
        await db.project_analyses.create_index(
            [("user_id", 1), ("analysis_timestamp", -1)]
        )

        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.warning("Index creation warning: %s", e)


app = FastAPI(
    title="KeyForge API",
    description="Universal API Infrastructure Assistant",
    version="2.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(auth_router)
app.include_router(credentials_router)
app.include_router(projects_router)
app.include_router(dashboard_router)

# CORS — allow the frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/")
async def root():
    return {"message": "KeyForge API Infrastructure Assistant", "version": "2.0.0"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception:
        return {"status": "degraded", "database": "disconnected"}
