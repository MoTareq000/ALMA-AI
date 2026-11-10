"""
Lesson Generations Polling API
==============================
Tracks background lesson generation progress.
Conforms strictly to the ALMA Express route convention:
    GET /api/v1/lesson-generations/job/{job_id}
    GET /api/v1/lesson-generations
"""

from typing import List
from fastapi import APIRouter, HTTPException, Depends
from ...storage import job_manager
from ..schemas import JobStatusResponse
from ..security import verify_api_key

router = APIRouter(
    prefix="/lesson-generations",
    tags=["Lesson Generations"],
    dependencies=[Depends(verify_api_key)]
)


@router.get("/job/{job_id}", response_model=JobStatusResponse)
@router.get("/{job_id}", response_model=JobStatusResponse, include_in_schema=False)
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


# Direct /jobs alias router for RESTful /jobs/{job_id} client calls
jobs_alias_router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
    dependencies=[Depends(verify_api_key)]
)


@jobs_alias_router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status_alias(job_id: str):
    """Check the progress of a lesson generation job by job ticket (/jobs/{job_id})."""
    return get_job_status(job_id)


@jobs_alias_router.get("", response_model=List[JobStatusResponse])
def list_jobs_alias():
    """List all tracked lesson generation jobs (/jobs)."""
    return list_generation_jobs()
