from typing import List, Optional
from pydantic import BaseModel, Field

class LessonSpec(BaseModel):
    """Specification submitted by a teacher to generate a programming lesson."""
    subject: str = Field(default="Programming", description="Subject area")
    topic: str = Field(..., description="Core lesson topic (e.g. 'For Loops in Python', 'Functions in JavaScript')")
    programming_language: str = Field(default="Python", description="Programming language (Python, JavaScript, C++, etc.)")
    grade_level: str = Field(default="Grade 8", description="Target grade/age level (e.g. 'Grade 8', 'High School')")
    language: str = Field(default="en", description="Lesson language ('en' for v1)")
    learning_objectives: List[str] = Field(..., min_length=1, max_length=8, description="List of learning objectives")
    desired_depth: str = Field(default="standard", description="'basic', 'standard', or 'deep'")
    prerequisites: List[str] = Field(default_factory=list, description="Prior concepts students know")
    curriculum_references: List[str] = Field(default_factory=list, description="Curriculum standards or codes")
    curriculum_scope_notes: Optional[str] = Field(default=None, description="Scope boundaries or pedagogical constraints extracted from curriculum reference")
    additional_instructions: Optional[str] = Field(default=None, description="Special teacher instructions")
    target_duration_minutes: Optional[int] = Field(default=15, description="Target total narration/teaching minutes")
    course_id: Optional[str] = Field(default=None, description="Associated Course ID (MongoDB ObjectId)")
    module_id: Optional[str] = Field(default=None, description="Associated Module ID (MongoDB ObjectId)")
    created_by: Optional[str] = Field(default=None, description="Authoring Teacher ID (MongoDB ObjectId)")
