import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from bson import ObjectId
from pydantic import BaseModel, Field

class JobRecord(BaseModel):
    """Tracks asynchronous lesson generation status aligned with ALMA LessonGeneration Mongoose schema."""
    job_id: str
    lesson_id: Optional[str] = None
    topic: Optional[str] = None
    programming_language: str = Field(default="Python")
    grade_level: str = Field(default="Grade 8")
    model: str = Field(default="gemini-3.5-flash-lite")
    course_id: Optional[str] = None
    module_id: Optional[str] = None
    requested_by: Optional[str] = None
    status: str = Field(default="pending", description="'pending', 'processing', 'completed', 'failed'")
    current_step: str = Field(
        default="queued",
        description="One of: 'queued', 'outline', 'sections', 'bridges', 'intro_conclusion', 'practice', 'segmenting', 'validating', 'completed', 'failed'"
    )
    progress_percent: float = Field(default=0.0, description="0.0 to 1.0")
    step_message: str = Field(default="Generation initialized...")
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class JobManager:
    """Tracking store for asynchronous generation jobs, persisting directly into ALMA's 'lesson_generations' collection."""

    def __init__(self):
        self._jobs: Dict[str, JobRecord] = {}
        try:
            from .mongo_client import get_mongo_db
            db = get_mongo_db()
            self._collection = db["lesson_generations"] if db is not None else None
            self._legacy_collection = db["lesson_jobs"] if db is not None else None
        except Exception:
            self._collection = None
            self._legacy_collection = None

    def _sync_to_mongo(self, job: JobRecord):
        if self._collection is None:
            return

        doc = job.model_dump()
        doc["updated_at"] = datetime.utcnow()

        # Format ObjectIds for Mongoose compatibility
        if job.course_id and ObjectId.is_valid(job.course_id):
            doc["course_id"] = ObjectId(job.course_id)
        if job.module_id and ObjectId.is_valid(job.module_id):
            doc["module_id"] = ObjectId(job.module_id)
        if job.requested_by and ObjectId.is_valid(job.requested_by):
            doc["requested_by"] = ObjectId(job.requested_by)

        try:
            self._collection.replace_one(
                {"job_id": job.job_id},
                doc,
                upsert=True
            )
            # Keep legacy collection in sync if it exists
            if self._legacy_collection is not None:
                self._legacy_collection.replace_one(
                    {"job_id": job.job_id},
                    job.model_dump(),
                    upsert=True
                )
        except Exception:
            pass

    def create_job(
        self,
        lesson_id: Optional[str] = None,
        topic: Optional[str] = None,
        programming_language: str = "Python",
        grade_level: str = "Grade 8",
        model: str = "gemini-3.5-flash-lite",
        course_id: Optional[str] = None,
        module_id: Optional[str] = None,
        requested_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> JobRecord:
        job_id = f"job_{uuid.uuid4().hex[:10]}"
        meta = metadata or {}
        job = JobRecord(
            job_id=job_id,
            lesson_id=lesson_id,
            topic=topic or meta.get("topic") or "General Programming",
            programming_language=programming_language or meta.get("language") or "Python",
            grade_level=grade_level or meta.get("grade_level") or "Grade 8",
            model=model or meta.get("model") or "gemini-3.5-flash-lite",
            course_id=course_id or meta.get("course_id"),
            module_id=module_id or meta.get("module_id"),
            requested_by=requested_by or meta.get("requested_by"),
            status="pending",
            current_step="queued",
            progress_percent=0.0,
            step_message="Generation initialized...",
            metadata=meta
        )
        self._jobs[job_id] = job
        self._sync_to_mongo(job)
        return job

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        job = self._jobs.get(job_id)
        if not job and self._collection is not None:
            try:
                doc = self._collection.find_one({"job_id": job_id})
                if not doc and self._legacy_collection is not None:
                    doc = self._legacy_collection.find_one({"job_id": job_id})
                if doc:
                    clean = {k: (str(v) if isinstance(v, ObjectId) else v) for k, v in doc.items() if k != "_id"}
                    job = JobRecord.model_validate(clean)
                    self._jobs[job_id] = job
            except Exception:
                pass
        return job

    def update_progress(self, job_id: str, step: str, progress: float, message: str):
        job = self.get_job(job_id)
        if job:
            job.status = "processing"
            job.current_step = step
            job.progress_percent = round(progress, 2)
            job.step_message = message
            self._sync_to_mongo(job)

    def complete_job(self, job_id: str, lesson_id: Optional[str] = None):
        job = self.get_job(job_id)
        if job:
            job.status = "completed"
            job.current_step = "completed"
            job.progress_percent = 1.0
            job.step_message = "Lesson generation & validation completed successfully!"
            job.completed_at = datetime.utcnow()
            if lesson_id:
                job.lesson_id = lesson_id
            self._sync_to_mongo(job)

    def fail_job(self, job_id: str, error_message: str):
        job = self.get_job(job_id)
        if job:
            job.status = "failed"
            job.current_step = "failed"
            job.error = error_message
            job.step_message = f"Failed: {error_message}"
            job.completed_at = datetime.utcnow()
            self._sync_to_mongo(job)

# Global job manager instance
job_manager = JobManager()
