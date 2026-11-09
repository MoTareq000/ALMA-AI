"""
Student Adaptive Runtime API
=============================
Endpoints that power the student-facing lesson experience:
personalized greetings, checkpoint diagnosis, and in-lesson Q&A.
Synchronized with ALMA's StudentLessonSession MongoDB schema.
"""

import uuid
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from ...storage import memory_store, student_repository, session_repository
from ...domain import LessonContent
from ..schemas import (
    StartLessonSessionRequest,
    StartLessonSessionResponse,
    PersonalizedWrapperResponse,
    CheckpointAnswerRequest,
    CheckpointAnswerResponse,
    AskAlmaRequest,
    AskAlmaResponse,
)

router = APIRouter(prefix="/runtime", tags=["Student Runtime"])


class CompleteLessonSessionRequest(BaseModel):
    session_id: str
    student_id: Optional[str] = "student_mohamad_001"


@router.get("/students/{student_id}")
def get_student(student_id: str):
    """Get a student's profile and learning history."""
    student = student_repository.get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student '{student_id}' not found")
    return student


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    """Get live runtime session status and checkpoint/dialogue logs."""
    record = session_repository.get_session(session_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return record


@router.post("/lessons/{lesson_id}/start", response_model=StartLessonSessionResponse)
def start_lesson(lesson_id: str, req: StartLessonSessionRequest):
    """
    Start a lesson session for a student.
    Generates a personalized greeting based on their name, streak, and past struggles,
    and initializes an active session document in MongoDB.
    """
    session = memory_store.lessons.get(lesson_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Lesson '{lesson_id}' not found")

    curr = session.current_version
    content: LessonContent = curr.content

    student = student_repository.get_student(req.student_id or "student_mohamad_001")
    if not student:
        student = student_repository.get_default_student()

    # Build personalized greeting
    name = student.first_name
    streak = student.current_streak
    struggles = [s.concept_label for s in student.struggling_concepts if s.times_wrong >= 2]

    greeting_parts = [f"Hey {name}!"]
    if streak >= 3:
        greeting_parts.append(f"Awesome job on your {streak}-lesson streak.")
    else:
        greeting_parts.append("Ready to learn something new today?")
    if struggles:
        greeting_parts.append(f"Remember last time we worked with {struggles[0]}? Today's lesson will make that crystal clear.")

    prefix_text = " ".join(greeting_parts)
    wrapper = PersonalizedWrapperResponse(
        prefix_audio_text=prefix_text,
        suffix_audio_text=f"Let's dive in, {name}!",
        student_name=name,
        streak=streak,
        struggling_concepts_addressed=struggles
    )

    total_segments = 0
    est_duration = 15.0
    if curr.segmentation:
        total_segments = curr.segmentation.total_segments
        est_duration = curr.segmentation.est_total_duration_minutes

    session_id = f"sess_{uuid.uuid4().hex[:8]}"

    # Persist live student lesson session in MongoDB
    session_repository.create_session(
        session_id=session_id,
        student_id=student.student_id,
        lesson_id=lesson_id,
        personalized_greeting=prefix_text
    )

    return StartLessonSessionResponse(
        session_id=session_id,
        lesson_id=lesson_id,
        lesson_title=content.title,
        student=student,
        personalized_wrapper=wrapper,
        total_segments=total_segments,
        est_duration_minutes=est_duration,
        segmentation=curr.segmentation
    )


@router.post("/lessons/{lesson_id}/checkpoints/answer", response_model=CheckpointAnswerResponse)
def answer_checkpoint(lesson_id: str, req: CheckpointAnswerRequest):
    """
    Student answers a checkpoint question.
    Returns whether they're correct, any detected misconception,
    and either advances them or routes them to remediation content.
    Persists checkpoint telemetry in MongoDB student_lesson_sessions.
    """
    session = memory_store.lessons.get(lesson_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Lesson '{lesson_id}' not found")

    curr = session.current_version
    section = next((s for s in curr.content.sections if s.order == req.section_order), None)
    if not section:
        raise HTTPException(status_code=404, detail=f"Section {req.section_order} not found")

    diag = section.diagnostic_check
    if not diag:
        raise HTTPException(status_code=400, detail="This section has no diagnostic checkpoint")

    chosen = (req.selected_option or req.selected_answer or req.student_answer_text or "").strip()
    is_correct = chosen.lower() == diag.correct_answer.strip().lower()

    misconception = None
    if not is_correct and diag.misconception_map:
        misconception = diag.misconception_map.get(chosen)

    student = student_repository.get_student(req.student_id or "student_mohamad_001")
    if not student:
        student = student_repository.get_default_student()

    concept_id = getattr(diag, "concept_tag", None) or f"section_{section.order}_concept"

    # Update student mastery tracking
    student_repository.record_checkpoint_result(
        student_id=student.student_id,
        concept_id=concept_id,
        concept_label=section.title,
        is_correct=is_correct,
        misconception=misconception
    )

    # Persist in student_lesson_sessions collection
    session_repository.log_checkpoint(
        session_id=req.session_id,
        section_order=req.section_order,
        selected_answer=chosen,
        is_correct=is_correct,
        detected_misconception=misconception,
        routed_to_remediation=not is_correct
    )

    if is_correct:
        return CheckpointAnswerResponse(
            is_correct=True,
            explanation=diag.explanation,
            detected_misconception=None,
            action="CONTINUE",
            remediation_blocks=None,
            current_streak=student.current_streak,
            feedback_message=f"Spot-on, {student.first_name}! {diag.explanation}"
        )

    # Wrong answer → route to remediation
    fb = f"Not quite, {student.first_name}."
    if misconception:
        fb += f" Note: {misconception}."
    fb += f" {diag.explanation}"

    return CheckpointAnswerResponse(
        is_correct=False,
        explanation=diag.explanation,
        detected_misconception=misconception,
        action="ROUTE_TO_REMEDIATION",
        remediation_blocks=section.remediation_blocks if section.remediation_blocks else [],
        current_streak=0,
        feedback_message=fb
    )


@router.post("/lessons/{lesson_id}/ask-alma", response_model=AskAlmaResponse)
def ask_alma(lesson_id: str, req: AskAlmaRequest):
    """Student asks a question — ALMA answers and logs dialogue to MongoDB."""
    session = memory_store.lessons.get(lesson_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Lesson '{lesson_id}' not found")

    curr = session.current_version
    section = next((s for s in curr.content.sections if s.order == req.current_section_order), None)
    sec_title = section.title if section else "this concept"

    student = student_repository.get_student(req.student_id or "student_mohamad_001")
    name = student.first_name if student else "Learner"

    # Find a relevant code block from the section
    ref_code = None
    if section:
        for b in section.blocks:
            if b.type == "code" and b.code:
                ref_code = b.code
                break

    spoken_answer = f"Great question, {name}! In {sec_title}, remember that code executes line-by-line in sequential order."

    # Persist dialogue in MongoDB
    session_repository.log_dialogue(
        session_id=req.session_id,
        section_order=req.current_section_order,
        question=req.question_text,
        spoken_answer=spoken_answer
    )

    return AskAlmaResponse(
        student_name=name,
        question=req.question_text,
        spoken_answer=spoken_answer,
        referenced_code=ref_code
    )


@router.post("/lessons/{lesson_id}/complete")
def complete_lesson(lesson_id: str, req: CompleteLessonSessionRequest):
    """Mark a student's lesson session completed and increment their completed count."""
    record = session_repository.complete_session(req.session_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Session '{req.session_id}' not found")

    student_id = req.student_id or record.student_id
    if hasattr(student_repository, "increment_lessons_completed"):
        student_repository.increment_lessons_completed(student_id)

    return {
        "status": "completed",
        "session_id": req.session_id,
        "completed_at": record.completed_at
    }
