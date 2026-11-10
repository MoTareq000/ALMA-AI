"""
Lesson Generations Polling API
==============================
Tracks background lesson generation progress.
Conforms strictly to the ALMA Express route convention:
    GET /api/v1/lesson-generations/job/{job_id}
    GET /api/v1/lesson-generations
"""

from typing import List
from fastapi import APIRouter, HTTPException
from ...storage import job_manager
from ..schemas import JobStatusResponse

router = APIRouter(prefix="/lesson-generations", tags=["Lesson Generations"])


@router.get("/job/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str):
    """Check the progress of a lesson generation job by its job ticket."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Lesson generation job '{job_id}' not found")
    return job


@router.get("", response_model=List[JobStatusResponse])
def list_generation_jobs():
    """List all tracked lesson generation jobs."""
    return job_manager.list_jobs()
