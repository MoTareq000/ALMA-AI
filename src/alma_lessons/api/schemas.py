"""
API Request & Response Schemas
===============================
Pydantic models that define what the API accepts and returns.
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field

from ..domain import (
    LessonSpec,
    LessonContent,
    Section,
    Block,
    LessonSegmentation,
)
from ..storage import StudentProfile


# ── Lesson Generation ────────────────────────────────────────────────

class LessonCreateRequest(BaseModel):
    """What the teacher submits to generate a lesson."""
    spec: LessonSpec
    provider: Optional[str] = Field(default="gemini", description="LLM provider: gemini, groq, or openrouter")
    model: Optional[str] = Field(default=None, description="Specific model name (leave empty to use provider default)")
    course_id: Optional[str] = Field(default=None, description="Optional Course ObjectId")
    module_id: Optional[str] = Field(default=None, description="Optional Module ObjectId")
    created_by: Optional[str] = Field(default=None, description="Optional Teacher ObjectId")

    model_config = {
        "json_schema_extra": {
            "example": {
                "spec": {
                    "subject": "Computer Science",
                    "topic": "For Loops in Python",
                    "programming_language": "Python",
                    "grade_level": "Grade 8",
                    "learning_objectives": [
                        "Understand loop repetition syntax with range()",
                        "Trace loop variables across iterations"
                    ],
                    "target_duration_minutes": 15
                },
                "provider": "gemini",
                "model": "gemini-3.5-flash-lite"
            }
        }
    }


class LessonSummaryResponse(BaseModel):
    """Lightweight lesson card for dashboard listing."""
    lesson_id: str
    title: str
    topic: str
    programming_language: str
    grade_level: str
    target_duration_minutes: int
    current_version_no: int
    current_state: str
    versions_count: int
    course_id: Optional[str] = None
    module_id: Optional[str] = None
    created_at: Union[datetime, str]


class LessonFullResponse(BaseModel):
    """Complete lesson data: content + validation + segmentation."""
    lesson_id: str
    spec: LessonSpec
    current_version_no: int
    approved_version_no: Optional[int] = None
    current_state: str
    content: LessonContent
    validation_report: Optional[Dict[str, Any]] = None
    segmentation: Optional[LessonSegmentation] = None
    course_id: Optional[str] = None
    module_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Union[datetime, str]


# ── Teacher Actions ──────────────────────────────────────────────────

class TeacherEditRequest(BaseModel):
    """Teacher modifies lesson content (creates a new version)."""
    title: str
    sections: List[Section]
    introduction: Optional[List[Block]] = None
    conclusion: Optional[List[Block]] = None


class ApproveLessonRequest(BaseModel):
    acknowledged_warnings: List[str] = Field(default_factory=list)


class RejectLessonRequest(BaseModel):
    rejection_reason: str = Field(default="Content scope unsuitable")


class RegenerateLessonRequest(BaseModel):
    """Teacher requests AI to re-generate the lesson with guidance notes."""
    teacher_feedback: str = Field(..., description="What should the AI improve or change")
    provider: Optional[str] = "gemini"
    model: Optional[str] = None


# ── Background Job Tracking ──────────────────────────────────────────

class JobStatusResponse(BaseModel):
    """Status of a background generation/regeneration job."""
    job_id: str
    lesson_id: Optional[str] = None
    topic: Optional[str] = None
    programming_language: Optional[str] = "Python"
    grade_level: Optional[str] = "Grade 8"
    model: Optional[str] = None
    course_id: Optional[str] = None
    module_id: Optional[str] = None
    requested_by: Optional[str] = None
    status: str
    current_step: str
    progress_percent: float
    step_message: str
    error: Optional[str] = None
    created_at: Union[datetime, str]
    completed_at: Optional[Union[datetime, str]] = None


# ── Curriculum ───────────────────────────────────────────────────────

class CurriculumExtractResponse(BaseModel):
    raw_text_length: int
    extracted_metadata: Dict[str, Any]
    suggested_spec: LessonSpec


# ── Student Runtime ──────────────────────────────────────────────────

class StartLessonSessionRequest(BaseModel):
    student_id: Optional[str] = Field(default="student_mohamad_001")


class PersonalizedWrapperResponse(BaseModel):
    prefix_audio_text: str
    suffix_audio_text: Optional[str] = None
    student_name: str
    streak: int
    struggling_concepts_addressed: List[str] = Field(default_factory=list)


class StartLessonSessionResponse(BaseModel):
    session_id: str
    lesson_id: str
    lesson_title: str
    student: StudentProfile
    personalized_wrapper: PersonalizedWrapperResponse
    total_segments: int
    est_duration_minutes: float
    segmentation: Optional[LessonSegmentation] = None


class CheckpointAnswerRequest(BaseModel):
    session_id: str
    student_id: str = "student_mohamad_001"
    section_order: int
    selected_option: Optional[str] = None
    selected_answer: Optional[str] = None
    student_answer_text: Optional[str] = None


class CheckpointAnswerResponse(BaseModel):
    is_correct: bool
    explanation: str
    detected_misconception: Optional[str] = None
    action: str = Field(description="'CONTINUE' or 'ROUTE_TO_REMEDIATION'")
    remediation_blocks: Optional[List[Block]] = None
    current_streak: int
    feedback_message: str


class AskAlmaRequest(BaseModel):
    session_id: str
    student_id: str = "student_mohamad_001"
    current_section_order: int
    question_text: str


class AskAlmaResponse(BaseModel):
    student_name: str
    question: str
    spoken_answer: str
    referenced_code: Optional[str] = None
