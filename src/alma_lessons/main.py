"""
ALMA Academy — FastAPI Backend Server
======================================
Entry point for the REST API. Run with:
    python -m uvicorn alma_lessons.main:app --app-dir src --host 127.0.0.1 --port 8000
"""

import sys
from pathlib import Path

# Ensure src is on sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from alma_lessons.api.routers import health, curriculum, jobs, lessons, runtime

app = FastAPI(
    title="ALMA Academy — AI Lesson Generation API",
    description="Generate, validate, and deliver AI-powered programming lessons.",
    version="1.0.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(health.router,     prefix="/api/v1")
app.include_router(curriculum.router, prefix="/api/v1")
app.include_router(jobs.router,       prefix="/api/v1")
app.include_router(lessons.router,    prefix="/api/v1")
app.include_router(runtime.router,    prefix="/api/v1")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("alma_lessons.main:app", host="0.0.0.0", port=8000, reload=True)
