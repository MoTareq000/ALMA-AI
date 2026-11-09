"""
Lesson Generation & Management API
===================================
All lesson-related endpoints: generate, list, view, edit, approve, reject, regenerate.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime

from ...storage import memory_store, job_manager
from ...generation import LessonGenerationPipeline
from ...segmentation import BasicLessonSegmenter
from ...validation import ValidationRunner
from ...domain import LessonContent, LessonSpec
from ..deps import get_llm_client
from ..schemas import (
    LessonCreateRequest,
    LessonSummaryResponse,
    LessonFullResponse,
    TeacherEditRequest,
    ApproveLessonRequest,
    RejectLessonRequest,
    RegenerateLessonRequest,
    JobStatusResponse,
)

router = APIRouter(prefix="/lessons", tags=["Lessons"])


# ---------------------------------------------------------------------------
# Background generation worker
# ---------------------------------------------------------------------------

def _run_generation(job_id: str, request: LessonCreateRequest):
    """Background task: runs the full generation pipeline and stores the result."""
    try:
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

    except Exception as e:
        job_manager.fail_job(job_id, str(e))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=JobStatusResponse, status_code=202)
def generate_lesson(request: LessonCreateRequest, background_tasks: BackgroundTasks):
    """
    Start generating a new lesson in the background.
    Returns a job_id you can poll with GET /api/v1/lesson-generations/job/{job_id}.
    """
    job = job_manager.create_job(
        topic=request.spec.topic,
        programming_language=request.spec.programming_language,
        grade_level=request.spec.grade_level,
        model=request.model or "gemini-3.5-flash-lite",
        course_id=request.course_id or request.spec.course_id,
        module_id=request.module_id or request.spec.module_id,
        requested_by=request.created_by or request.spec.created_by,
        metadata={"topic": request.spec.topic, "language": request.spec.programming_language}
    )
    background_tasks.add_task(_run_generation, job.job_id, request)
    return job


@router.get("", response_model=List[LessonSummaryResponse])
def list_lessons():
    """List all generated lessons (lightweight summary for dashboard)."""
    results = []
    for s in memory_store.lessons.values():
        curr = s.current_version
        results.append(LessonSummaryResponse(
            lesson_id=s.lesson_id,
            title=curr.content.title,
            topic=s.spec.topic,
            programming_language=s.spec.programming_language,
            grade_level=s.spec.grade_level,
            target_duration_minutes=s.spec.target_duration_minutes or 15,
            current_version_no=s.current_version_no,
            current_state=curr.state.value,
            versions_count=len(s.versions),
            course_id=getattr(s.spec, "course_id", None),
            module_id=getattr(s.spec, "module_id", None),
            created_at=s.created_at
        ))
    return results


@router.get("/sync/all")
def sync_all_lessons():
    """Returns all lesson data for frontend cache sync."""
    return {lid: s.model_dump() for lid, s in memory_store.lessons.items()}


@router.get("/{lesson_id}", response_model=LessonFullResponse)
def get_lesson(lesson_id: str):
    """Get a lesson's full content, validation report, and segmentation."""
    session = memory_store.lessons.get(lesson_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Lesson '{lesson_id}' not found")

    curr = session.current_version
    return LessonFullResponse(
        lesson_id=session.lesson_id,
        spec=session.spec,
        current_version_no=session.current_version_no,
        approved_version_no=session.approved_version_no,
        current_state=curr.state.value,
        content=curr.content,
        validation_report=curr.validation_report,
        segmentation=curr.segmentation,
        course_id=getattr(session.spec, "course_id", None),
        module_id=getattr(session.spec, "module_id", None),
        created_by=getattr(session.spec, "created_by", None),
        created_at=session.created_at
    )


@router.put("/{lesson_id}/edit", response_model=LessonFullResponse, status_code=201)
def edit_lesson(lesson_id: str, edit_req: TeacherEditRequest):
    """
    Teacher saves edits. Creates a new immutable version (v2, v3, ...).
    The old version is preserved — nothing is overwritten.
    """
    session = memory_store.lessons.get(lesson_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Lesson '{lesson_id}' not found")

    old_content = session.current_version.content

    edited_content = LessonContent(
        title=edit_req.title,
        programming_language=old_content.programming_language,
        grade_level=old_content.grade_level,
        target_duration_minutes=session.spec.target_duration_minutes or 15,
        introduction=edit_req.introduction if edit_req.introduction else old_content.introduction,
        objectives=old_content.objectives,
        sections=edit_req.sections,
        conclusion=edit_req.conclusion if edit_req.conclusion else old_content.conclusion,
        puzzles=old_content.puzzles,
        exercises=old_content.exercises,
    )

    # Revalidate and resegment
    validator = ValidationRunner()
    report = validator.run(edited_content, session.spec)

    segmenter = BasicLessonSegmenter()
    client = get_llm_client()
    pipeline = LessonGenerationPipeline(llm_client=client)
    seg = segmenter.segment_lesson(
        edited_content,
        spec=session.spec,
        topic_assessment_generator=pipeline.generate_topic_micro_checks
    )

    new_ver = memory_store.add_teacher_edit(
        lesson_id=lesson_id,
        edited_content=edited_content,
        revalidation_report=report,
        segmentation=seg
    )

    return LessonFullResponse(
        lesson_id=session.lesson_id,
        spec=session.spec,
        current_version_no=new_ver.version_no,
        approved_version_no=session.approved_version_no,
        current_state=new_ver.state.value,
        content=new_ver.content,
        validation_report=new_ver.validation_report,
        segmentation=new_ver.segmentation,
        course_id=getattr(session.spec, "course_id", None),
        module_id=getattr(session.spec, "module_id", None),
        created_by=getattr(session.spec, "created_by", None),
        created_at=new_ver.created_at
    )


@router.post("/{lesson_id}/approve")
def approve_lesson(lesson_id: str, req: ApproveLessonRequest):
    """Teacher approves the current version. Locks the lesson as final."""
    session = memory_store.lessons.get(lesson_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Lesson '{lesson_id}' not found")

    curr = session.current_version
    report = curr.validation_report or {}
    if report.get("has_blocking_errors", False):
        raise HTTPException(status_code=400, detail="Cannot approve: there are blocking validation errors")

    approved = memory_store.approve_lesson(
        lesson_id=lesson_id,
        acknowledged_warnings=req.acknowledged_warnings,
        segmentation=curr.segmentation
    )

    return {
        "status": "APPROVED",
        "lesson_id": lesson_id,
        "version_no": approved.version_no,
        "content_hash": approved.content_hash,
    }


@router.post("/{lesson_id}/reject")
def reject_lesson(lesson_id: str, req: RejectLessonRequest):
    """Teacher rejects the current version with a reason."""
    session = memory_store.lessons.get(lesson_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Lesson '{lesson_id}' not found")

    rejected = memory_store.reject_lesson(lesson_id, req.rejection_reason)
    return {
        "status": "REJECTED",
        "lesson_id": lesson_id,
        "version_no": rejected.version_no,
        "reason": req.rejection_reason,
    }


def _run_regeneration(job_id: str, lesson_id: str, req: RegenerateLessonRequest):
    """Background task for regeneration with teacher feedback."""
    try:
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

    except Exception as e:
        job_manager.fail_job(job_id, str(e))


@router.post("/{lesson_id}/regenerate", response_model=JobStatusResponse, status_code=202)
def regenerate_lesson(lesson_id: str, req: RegenerateLessonRequest, background_tasks: BackgroundTasks):
    """Re-generate the lesson using teacher feedback notes."""
    session = memory_store.lessons.get(lesson_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Lesson '{lesson_id}' not found")

    job = job_manager.create_job(
        lesson_id=lesson_id,
        topic=session.spec.topic,
        programming_language=session.spec.programming_language,
        grade_level=session.spec.grade_level,
        model=req.model or "gemini-3.5-flash-lite",
        course_id=getattr(session.spec, "course_id", None),
        module_id=getattr(session.spec, "module_id", None),
        requested_by=getattr(session.spec, "created_by", None),
        metadata={"feedback": req.teacher_feedback}
    )
    background_tasks.add_task(_run_regeneration, job.job_id, lesson_id, req)
    return job
