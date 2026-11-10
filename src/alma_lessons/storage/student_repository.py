from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class ConceptMasteryItem(BaseModel):
    concept_id: str
    concept_label: str
    times_tested: int = 0
    times_correct: int = 0
    times_wrong: int = 0
    last_misconception: Optional[str] = None
    last_assessed: Optional[datetime] = None

class StudentPreferences(BaseModel):
    pacing: str = Field(default="standard", description="'slow', 'standard', or 'fast'")
    tone: str = Field(default="encouraging", description="'encouraging', 'direct', or 'gamified'")
    voice_id: str = Field(default="en-US-Journey-F", description="Preferred TTS voice model")
    language: str = Field(default="en", description="'en' or 'ar'")

class StudentProfile(BaseModel):
    student_id: str
    first_name: str
    last_name: str
    email: str
    student_code: str
    grade_level: str
    school_name: Optional[str] = "ALMA Academy"
    lessons_completed: int = 0
    current_streak: int = 0
    struggling_concepts: List[ConceptMasteryItem] = Field(default_factory=list)
    preferences: StudentPreferences = Field(default_factory=StudentPreferences)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BaseStudentRepository:
    """Abstract interface for Student Data Access.
    Allows seamlessly swapping this local memory implementation with MongoDB (Motor / PyMongo)
    when connecting to the production database.
    """
    def get_student(self, student_id: str) -> Optional[StudentProfile]:
        raise NotImplementedError

    def update_student_streak(self, student_id: str, new_streak: int) -> Optional[StudentProfile]:
        raise NotImplementedError

    def record_checkpoint_result(
        self,
        student_id: str,
        concept_id: str,
        concept_label: str,
        is_correct: bool,
        misconception: Optional[str] = None
    ) -> Optional[StudentProfile]:
        raise NotImplementedError


class LocalStudentRepository(BaseStudentRepository):
    """In-memory local student repository.
    Only seeds demo student when ALMA_SEED_DEMO_DATA=true.
    """
    def __init__(self):
        self._students: Dict[str, StudentProfile] = {}
        from ..config import config
        if config.alma_seed_demo_data:
            self._seed_default_data()

    def _seed_default_data(self):
        # Pre-seed with demo student Mohamad
        mohamad = StudentProfile(
            student_id="student_mohamad_001",
            first_name="Mohamad",
            last_name="Ali",
            email="mohamad.ali@alma.edu",
            student_code="STD-MOH-2026",
            grade_level="Grade 8",
            school_name="ALMA Academy (Cairo Campus)",
            lessons_completed=4,
            current_streak=3,
            struggling_concepts=[
                ConceptMasteryItem(
                    concept_id="python.loops.range",
                    concept_label="range() function parameters",
                    times_tested=3,
                    times_correct=1,
                    times_wrong=2,
                    last_misconception="Off-by-one: assumed range(1, 5) includes the stop number 5",
                    last_assessed=datetime.now(timezone.utc)
                )
            ],
            preferences=StudentPreferences(
                pacing="standard",
                tone="encouraging",
                voice_id="en-US-Journey-F",
                language="en"
            )
        )
        self._students[mohamad.student_id] = mohamad

    def create_student(self, profile: StudentProfile) -> StudentProfile:
        self._students[profile.student_id] = profile
        return profile

    def get_student(self, student_id: str) -> Optional[StudentProfile]:
        return self._students.get(student_id)

    def get_default_student(self) -> Optional[StudentProfile]:
        if "student_mohamad_001" in self._students:
            return self._students["student_mohamad_001"]
        if self._students:
            return next(iter(self._students.values()))
        return None

    def list_students(self) -> List[StudentProfile]:
        return list(self._students.values())

    def update_student_streak(self, student_id: str, new_streak: int) -> Optional[StudentProfile]:
        student = self._students.get(student_id)
        if student:
            student.current_streak = new_streak
        return student

    def record_checkpoint_result(
        self,
        student_id: str,
        concept_id: str,
        concept_label: str,
        is_correct: bool,
        misconception: Optional[str] = None
    ) -> Optional[StudentProfile]:
        student = self._students.get(student_id)
        if not student:
            return None

        # Find or create concept mastery
        item = next((c for c in student.struggling_concepts if c.concept_id == concept_id), None)
        if not item:
            item = ConceptMasteryItem(
                concept_id=concept_id,
                concept_label=concept_label,
                times_tested=0,
                times_correct=0,
                times_wrong=0
            )
            student.struggling_concepts.append(item)

        item.times_tested += 1
        item.last_assessed = datetime.now(timezone.utc)
        if is_correct:
            item.times_correct += 1
            student.current_streak += 1
        else:
            item.times_wrong += 1
            student.current_streak = 0
            if misconception:
                item.last_misconception = misconception

        return student

    def increment_lessons_completed(self, student_id: str) -> Optional[StudentProfile]:
        student = self._students.get(student_id)
        if student:
            student.lessons_completed += 1
        return student

# Global singleton instance
student_repository = LocalStudentRepository()
