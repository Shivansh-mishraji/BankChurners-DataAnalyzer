"""
server.py
=========
FastAPI application entry point for Bank Churner Analytics Web Dashboard.
Serves both the REST API and the static frontend.

Run with:
    uvicorn server:app --reload --port 8000
"""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.data import router as data_router

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Bank Churner Analytics API",
    version="2.0.0",
    description="REST API powering the Bank Churner Analytics web dashboard.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Allow all origins in development — tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ── API routes ────────────────────────────────────────────────────────────────
app.include_router(data_router, prefix="/api/v1", tags=["Data"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


# ── Serve static frontend ─────────────────────────────────────────────────────
STATIC_DIR = Path(__file__).parent / "frontend"

if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str = ""):
        # Don't intercept API or asset routes
        if full_path.startswith(("api", "assets")):
            return {"error": "Not found"}
        index = STATIC_DIR / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return {"error": "Frontend not found."}
else:
    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "message": "Bank Churner Analytics API is running.",
            "docs": "/api/docs",
            "health": "/api/health",
        }


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Bank Churner Analytics server on http://localhost:8000")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
