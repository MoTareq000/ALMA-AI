import logging
from typing import Dict, Any
from datetime import datetime, timezone

from ..config import config
from ..storage import memory_store, job_manager
from ..storage.mongo_client import get_mongo_db, is_mongo_connected
from ..generation import LessonGenerationPipeline
from ..segmentation import BasicLessonSegmenter
from ..validation import ValidationRunner
from ..api.deps import get_llm_client
from ..api.schemas import LessonCreateRequest, RegenerateLessonRequest

logger = logging.getLogger(__name__)


def cleanup_stale_jobs_on_startup():
    """On API or worker startup, scan for any jobs left in 'pending' or 'processing'
    by an interrupted/dead process, and fail or requeue them cleanly.
    """
    if not is_mongo_connected():
        return

    db = get_mongo_db()
    if db is None:
        return

    collection = db["lesson_generations"]
    stale_query = {"status": {"$in": ["pending", "processing"]}}

    try:
        stale_count = collection.count_documents(stale_query)
        if stale_count > 0:
            logger.warning(f"Found {stale_count} stale generation jobs in MongoDB. Updating status...")
            now = datetime.now(timezone.utc)
            if config.job_backend == "rq":
                # With RQ, notify or mark for inspection
                collection.update_many(
                    stale_query,
                    {
                        "$set": {
                            "status": "failed",
                            "current_step": "failed",
                            "error": "Process terminated unexpectedly. Requeued or marked failed on startup.",
                            "completed_at": now,
                            "updated_at": now,
                        }
                    }
                )
            else:
                collection.update_many(
                    stale_query,
                    {
                        "$set": {
                            "status": "failed",
                            "current_step": "failed",
                            "error": "Server restarted while generation was in progress.",
                            "completed_at": now,
                            "updated_at": now,
                        }
                    }
                )
            logger.info(f"Marked {stale_count} interrupted jobs as failed on startup.")
    except Exception as e:
        logger.warning(f"Error during stale jobs cleanup: {e}")


def run_generation_task(job_id: str, request_dict: Dict[str, Any]):
    """Execute the full AI lesson generation pipeline for a job."""
    try:
        request = LessonCreateRequest.model_validate(request_dict)

        # Align spec metadata
        if request.course_id and not request.spec.course_id:
            request.spec.course_id = request.course_id
        if request.module_id and not request.spec.module_id:
            request.spec.module_id = request.module_id
        if request.created_by and not request.spec.created_by:
            request.spec.created_by = request.created_by

        llm_client = get_llm_client(provider=request.provider, model=request.model)
        pipeline = LessonGenerationPipeline(llm_client=llm_client)

        def on_progress(msg: str, pct: float):
            step = "sections"
            if "outline" in msg.lower():
                step = "outline"
            elif "bridge" in msg.lower():
                step = "bridges"
            elif "intro" in msg.lower():
                step = "intro_conclusion"
            elif "puzzle" in msg.lower() or "practice" in msg.lower():
                step = "practice"
            job_manager.update_progress(job_id, step=step, progress=pct * 0.8, message=msg)

        # 1. Generate lesson content
        lesson_content, outline = pipeline.run(request.spec, progress_callback=on_progress)

        # 2. Segment into ~45-60s narration chunks
        job_manager.update_progress(job_id, step="segmenting", progress=0.85, message="Creating audio narration segments...")
        segmenter = BasicLessonSegmenter()
        segmentation = segmenter.segment_lesson(
            lesson_content,
            spec=request.spec,
            topic_assessment_generator=pipeline.generate_topic_micro_checks
        )

        # 3. Validate
        job_manager.update_progress(job_id, step="validating", progress=0.95, message="Running validation checks...")
        validator = ValidationRunner()
        report = validator.run(lesson_content, request.spec)

        # 4. Store
        session = memory_store.create_lesson(
            spec=request.spec,
            content=lesson_content,
            validation_report=report,
            segmentation=segmentation
        )

        job_manager.complete_job(job_id, lesson_id=session.lesson_id)
        return session.lesson_id

    except Exception as e:
        logger.error(f"Generation task failed for job {job_id}: {e}")
        job_manager.fail_job(job_id, str(e))
        raise e


def run_regeneration_task(job_id: str, lesson_id: str, request_dict: Dict[str, Any]):
    """Execute AI re-generation pipeline using teacher feedback."""
    try:
        req = RegenerateLessonRequest.model_validate(request_dict)
        session = memory_store.lessons.get(lesson_id)
        if not session:
            job_manager.fail_job(job_id, f"Lesson '{lesson_id}' not found")
            return

        llm_client = get_llm_client(provider=req.provider, model=req.model)
        pipeline = LessonGenerationPipeline(llm_client=llm_client)

        def on_progress(msg: str, pct: float):
            step = "sections"
            if "outline" in msg.lower():
                step = "outline"
            elif "bridge" in msg.lower():
                step = "bridges"
            elif "intro" in msg.lower():
                step = "intro_conclusion"
            elif "puzzle" in msg.lower() or "practice" in msg.lower():
                step = "practice"
            job_manager.update_progress(job_id, step=step, progress=pct * 0.8, message=msg)

        new_lesson, _ = pipeline.run(
            session.spec,
            teacher_feedback=req.teacher_feedback,
            progress_callback=on_progress
        )

        job_manager.update_progress(job_id, step="segmenting", progress=0.85, message="Re-segmenting narration chunks...")
        segmenter = BasicLessonSegmenter()
        seg = segmenter.segment_lesson(
            new_lesson,
            spec=session.spec,
            topic_assessment_generator=pipeline.generate_topic_micro_checks
        )

        job_manager.update_progress(job_id, step="validating", progress=0.95, message="Validating regenerated content...")
        validator = ValidationRunner()
        report = validator.run(new_lesson, session.spec)

        new_ver = memory_store.add_regeneration(
            lesson_id=lesson_id,
            new_content=new_lesson,
            feedback=req.teacher_feedback,
            validation_report=report
        )
        new_ver.segmentation = seg

        job_manager.complete_job(job_id, lesson_id=lesson_id)
        return lesson_id

    except Exception as e:
        logger.error(f"Regeneration task failed for job {job_id}: {e}")
        job_manager.fail_job(job_id, str(e))
        raise e

