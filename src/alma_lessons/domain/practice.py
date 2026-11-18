import uuid
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from .assessment import PuzzleChallenge, CodingExercise


class PracticeSet(BaseModel):
    """Standalone Course Practice Challenge Set decoupled from lessons."""
    practice_id: str = Field(default_factory=lambda: f"prac_{uuid.uuid4().hex[:10]}")
    topic: str = Field(..., description="Topic of this practice set (e.g. 'For Loops in Python')")
    course_id: Optional[str] = Field(default=None, description="Associated Course ID")
    module_id: Optional[str] = Field(default=None, description="Associated Module ID")
    programming_language: str = Field(default="Python", description="Programming language")
    grade_level: str = Field(default="Grade 8", description="Target grade/level")
    concepts_covered: List[str] = Field(default_factory=list, description="Key concepts covered in this set")
    puzzles: List[PuzzleChallenge] = Field(default_factory=list, description="Parsons problems and code-tracing puzzles")
    exercises: List[CodingExercise] = Field(default_factory=list, description="Tiered difficulty coding challenges")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PracticeCreateRequest(BaseModel):
    """Payload to trigger generation of a new course practice challenge set."""
    topic: str = Field(..., description="Topic for practice challenges (e.g. 'Python Loops & Iteration')")
    course_id: Optional[str] = Field(default=None, description="Optional Course ID")
    module_id: Optional[str] = Field(default=None, description="Optional Module ID")
    programming_language: str = Field(default="Python", description="Programming language")
    grade_level: str = Field(default="Grade 8", description="Target grade/level")
    concepts_to_cover: List[str] = Field(default_factory=list, description="Specific concepts to focus on")
    provider: Optional[str] = Field(default="google", description="LLM provider")
    model: Optional[str] = Field(default=None, description="LLM model ID")


class PracticeSubmissionRequest(BaseModel):
    """Student submission for testing code in the practice arena."""
    student_id: str = Field(..., description="ID of student solving the challenge")
    current_difficulty: str = Field(default="medium", description="easy, medium, or hard")
    submitted_code: str = Field(..., description="Student code solution")
    hints_used: int = Field(default=0, description="Number of hints unlocked")
