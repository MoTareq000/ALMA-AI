import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from bson import ObjectId

from .student_repository import (
    BaseStudentRepository,
    StudentProfile,
    ConceptMasteryItem,
    StudentPreferences,
)
from .mongo_client import get_mongo_db

logger = logging.getLogger(__name__)

class MongoStudentRepository(BaseStudentRepository):
    """MongoDB implementation of BaseStudentRepository.
    Persists student profiles and adaptive mastery tracking in the ALMA MongoDB database.
    """

    def __init__(self):
        self.db = get_mongo_db()
        self.collection = self.db["students"] if self.db is not None else None
        from ..config import config
        if config.alma_seed_demo_data:
            self._seed_default_mohamad_if_needed()

    def create_student(self, profile: StudentProfile) -> StudentProfile:
        if self.collection is not None:
            doc = profile.model_dump()
            self.collection.replace_one({"student_id": profile.student_id}, doc, upsert=True)
        return profile

    def _seed_default_mohamad_if_needed(self):
        if self.collection is None:
            return
        # Check if student_mohamad_001 exists
        existing = self.collection.find_one({
            "$or": [
                {"student_id": "student_mohamad_001"},
                {"student_code": "STD-MOH-2026"}
            ]
        })
        if not existing:
            mohamad_doc = {
                "student_id": "student_mohamad_001",
                "first_name": "Mohamad",
                "last_name": "Ali",
                "email": "mohamad.ali@alma.edu",
                "student_code": "STD-MOH-2026",
                "grade_level": "Grade 8",
                "school_name": "ALMA Academy (Cairo Campus)",
                "lessons_completed": 4,
                "current_streak": 3,
                "struggling_concepts": [
                    {
                        "concept_id": "python.loops.range",
                        "concept_label": "range() function parameters",
                        "times_tested": 3,
                        "times_correct": 1,
                        "times_wrong": 2,
                        "last_misconception": "Off-by-one: assumed range(1, 5) includes the stop number 5",
                        "last_assessed": datetime.now(timezone.utc)
                    }
                ],
                "preferences": {
                    "pacing": "standard",
                    "tone": "encouraging",
                    "voice_id": "en-US-Journey-F",
                    "language": "en"
                },
                "created_at": datetime.now(timezone.utc)
            }
            self.collection.insert_one(mohamad_doc)
            logger.info("Seeded default student Mohamad into MongoDB 'students' collection.")

    def _doc_to_profile(self, doc: Dict[str, Any]) -> StudentProfile:
        """Convert a Mongo document to StudentProfile model."""
        student_id = doc.get("student_id") or doc.get("student_code") or str(doc.get("_id"))

        # Parse struggling concepts
        raw_struggles = doc.get("struggling_concepts", [])
        struggling_concepts = []
        for s in raw_struggles:
            if isinstance(s, dict):
                misconception = s.get("last_misconception") or s.get("last_diagnosed_misconception")
                struggling_concepts.append(ConceptMasteryItem(
                    concept_id=s.get("concept_id", "general"),
                    concept_label=s.get("concept_label", "General Concept"),
                    times_tested=s.get("times_tested", 0),
                    times_correct=s.get("times_correct", 0),
                    times_wrong=s.get("times_wrong", 0),
                    last_misconception=misconception,
                    last_assessed=s.get("last_assessed") or datetime.now(timezone.utc)
                ))

        # Parse preferences
        raw_pref = doc.get("preferences", {})
        if not isinstance(raw_pref, dict):
            raw_pref = {}
        pref = StudentPreferences(
            pacing=raw_pref.get("pacing", "standard"),
            tone=raw_pref.get("tone", "encouraging"),
            voice_id=raw_pref.get("voice_id", "en-US-Journey-F"),
            language=raw_pref.get("language", "en")
        )

        return StudentProfile(
            student_id=student_id,
            first_name=doc.get("first_name", "Student"),
            last_name=doc.get("last_name", ""),
            email=doc.get("email", ""),
            student_code=doc.get("student_code", student_id),
            grade_level=doc.get("grade_level", "Grade 8"),
            school_name=doc.get("school_name", "ALMA Academy"),
            lessons_completed=doc.get("lessons_completed", 0),
            current_streak=doc.get("current_streak", 0),
            struggling_concepts=struggling_concepts,
            preferences=pref,
            created_at=doc.get("created_at") if isinstance(doc.get("created_at"), datetime) else datetime.now(timezone.utc)
        )

    def _build_filter(self, student_id: str) -> Dict[str, Any]:
        """Build a flexible filter matching student_id, student_code, or ObjectId."""
        filters = [
            {"student_id": student_id},
            {"student_code": student_id}
        ]
        if ObjectId.is_valid(student_id):
            filters.append({"_id": ObjectId(student_id)})
        return {"$or": filters}

    def get_student(self, student_id: str) -> Optional[StudentProfile]:
        if self.collection is None:
            return None
        doc = self.collection.find_one(self._build_filter(student_id))
        return self._doc_to_profile(doc) if doc else None

    def get_default_student(self) -> Optional[StudentProfile]:
        first = self.collection.find_one() if self.collection is not None else None
        if first:
            return self._doc_to_profile(first)
        return None

    def list_students(self) -> List[StudentProfile]:
        if self.collection is None:
            return []
        return [self._doc_to_profile(doc) for doc in self.collection.find()]

    def update_student_streak(self, student_id: str, new_streak: int) -> Optional[StudentProfile]:
        if self.collection is None:
            return None
        filt = self._build_filter(student_id)
        self.collection.update_one(filt, {"$set": {"current_streak": new_streak, "updated_at": datetime.now(timezone.utc)}})
        return self.get_student(student_id)

    def record_checkpoint_result(
        self,
        student_id: str,
        concept_id: str,
        concept_label: str,
        is_correct: bool,
        misconception: Optional[str] = None
    ) -> Optional[StudentProfile]:
        if self.collection is None:
            return None

        doc = self.collection.find_one(self._build_filter(student_id))
        if not doc:
            return None

        struggling_concepts = doc.get("struggling_concepts", [])
        found = False
        for c in struggling_concepts:
            if c.get("concept_id") == concept_id:
                c["times_tested"] = c.get("times_tested", 0) + 1
                c["last_assessed"] = datetime.now(timezone.utc)
                if is_correct:
                    c["times_correct"] = c.get("times_correct", 0) + 1
                else:
                    c["times_wrong"] = c.get("times_wrong", 0) + 1
                    if misconception:
                        c["last_misconception"] = misconception
                        c["last_diagnosed_misconception"] = misconception
                found = True
                break

        if not found:
            new_item = {
                "concept_id": concept_id,
                "concept_label": concept_label,
                "times_tested": 1,
                "times_correct": 1 if is_correct else 0,
                "times_wrong": 0 if is_correct else 1,
                "last_misconception": misconception if not is_correct else None,
                "last_diagnosed_misconception": misconception if not is_correct else None,
                "last_assessed": datetime.now(timezone.utc)
            }
            struggling_concepts.append(new_item)

        current_streak = doc.get("current_streak", 0)
        new_streak = current_streak + 1 if is_correct else 0
        longest_streak = max(doc.get("longest_streak", 0), new_streak)

        self.collection.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "struggling_concepts": struggling_concepts,
                    "current_streak": new_streak,
                    "longest_streak": longest_streak,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        return self.get_student(student_id)

    def increment_lessons_completed(self, student_id: str) -> Optional[StudentProfile]:
        if self.collection is None:
            return None
        filt = self._build_filter(student_id)
        self.collection.update_one(filt, {"$inc": {"lessons_completed": 1}, "$set": {"updated_at": datetime.now(timezone.utc)}})
        return self.get_student(student_id)
