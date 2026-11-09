import json
import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from ..domain import LessonSpec, LessonContent, LessonState, LessonSegmentation, validate_transition

import hashlib

class LessonVersionRecord(BaseModel):
    """An immutable version record in memory."""
    version_no: int
    source: str  # "generated", "teacher_edit", "regenerated"
    state: LessonState
    content: LessonContent
    validation_report: Optional[Dict[str, Any]] = None
    segmentation: Optional[LessonSegmentation] = None
    teacher_feedback: Optional[str] = None
    rejection_reason: Optional[str] = None
    acknowledged_warnings: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.content.model_dump_json().encode()).hexdigest()[:16]

    @property
    def parent_version_no(self) -> Optional[int]:
        return self.version_no - 1 if self.version_no > 1 else None


class LessonSession(BaseModel):
    """A complete session for a lesson with version history."""
    lesson_id: str
    spec: LessonSpec
    current_version_no: int
    created_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    versions: List[LessonVersionRecord] = Field(default_factory=list)
    status_history: List[Dict[str, str]] = Field(default_factory=list)

    @property
    def current_version(self) -> Optional[LessonVersionRecord]:
        for v in reversed(self.versions):
            if v.version_no == self.current_version_no:
                return v
        return self.versions[-1] if self.versions else None

    @property
    def approved_version_no(self) -> Optional[int]:
        for v in self.versions:
            if v.state == LessonState.APPROVED:
                return v.version_no
        return None


class MemoryLessonStore:
    """In-memory store for managing lessons, version history, and state transitions with JSON export/import."""

    def __init__(self):
        self.lessons: Dict[str, LessonSession] = {}
        self._next_id = 1

    def create_lesson(
        self,
        spec: LessonSpec,
        content: LessonContent,
        validation_report: Optional[Dict[str, Any]] = None,
        segmentation: Optional[LessonSegmentation] = None,
    ) -> LessonSession:
        lesson_id = f"lesson_{self._next_id}"
        self._next_id += 1

        v1 = LessonVersionRecord(
            version_no=1,
            source="generated",
            state=LessonState.AWAITING_REVIEW,
            content=content,
            validation_report=validation_report,
            segmentation=segmentation,
        )

        session = LessonSession(
            lesson_id=lesson_id,
            spec=spec,
            current_version_no=1,
            versions=[v1],
            status_history=[{
                "from": LessonState.DRAFT.value,
                "to": LessonState.AWAITING_REVIEW.value,
                "at": datetime.datetime.now().isoformat(),
                "reason": "Initial generation pass completed and validated"
            }]
        )
        self.lessons[lesson_id] = session
        return session

    def add_teacher_edit(
        self,
        lesson_id: str,
        edited_content: LessonContent,
        revalidation_report: Optional[Dict[str, Any]] = None,
        segmentation: Optional[LessonSegmentation] = None,
    ) -> LessonVersionRecord:
        session = self.lessons.get(lesson_id)
        if not session:
            raise KeyError(f"Lesson not found: {lesson_id}")

        new_v_no = len(session.versions) + 1
        new_version = LessonVersionRecord(
            version_no=new_v_no,
            source="teacher_edit",
            state=LessonState.AWAITING_REVIEW,
            content=edited_content,
            validation_report=revalidation_report,
            segmentation=segmentation,
        )
        session.versions.append(new_version)
        session.current_version_no = new_v_no
        session.status_history.append({
            "from": session.versions[-2].state.value,
            "to": LessonState.AWAITING_REVIEW.value,
            "at": datetime.datetime.now().isoformat(),
            "reason": f"Teacher saved edits as version v{new_v_no}"
        })
        return new_version

    def add_regeneration(
        self,
        lesson_id: str,
        new_content: LessonContent,
        feedback: str,
        validation_report: Optional[Dict[str, Any]] = None
    ) -> LessonVersionRecord:
        session = self.lessons.get(lesson_id)
        if not session:
            raise KeyError(f"Lesson not found: {lesson_id}")

        new_v_no = len(session.versions) + 1
        new_version = LessonVersionRecord(
            version_no=new_v_no,
            source="regenerated",
            state=LessonState.AWAITING_REVIEW,
            content=new_content,
            validation_report=validation_report,
            teacher_feedback=feedback,
        )
        session.versions.append(new_version)
        session.current_version_no = new_v_no
        session.status_history.append({
            "from": session.versions[-2].state.value,
            "to": LessonState.AWAITING_REVIEW.value,
            "at": datetime.datetime.now().isoformat(),
            "reason": f"Regenerated with teacher feedback as v{new_v_no}"
        })
        return new_version

    def approve_lesson(
        self,
        lesson_id: str,
        acknowledged_warnings: List[str],
        segmentation: Optional[LessonSegmentation] = None
    ) -> LessonVersionRecord:
        session = self.lessons.get(lesson_id)
        if not session:
            raise KeyError(f"Lesson not found: {lesson_id}")

        curr = session.current_version
        if not curr:
            raise ValueError("No active version found")

        curr.state = LessonState.APPROVED
        curr.acknowledged_warnings = acknowledged_warnings
        curr.segmentation = segmentation

        session.status_history.append({
            "from": LessonState.AWAITING_REVIEW.value,
            "to": LessonState.APPROVED.value,
            "at": datetime.datetime.now().isoformat(),
            "reason": "Approved by teacher"
        })
        return curr

    def reject_lesson(self, lesson_id: str, reason: str) -> LessonVersionRecord:
        session = self.lessons.get(lesson_id)
        if not session:
            raise KeyError(f"Lesson not found: {lesson_id}")

        curr = session.current_version
        if not curr:
            raise ValueError("No active version found")

        curr.state = LessonState.REJECTED
        curr.rejection_reason = reason

        session.status_history.append({
            "from": curr.state.value,
            "to": LessonState.REJECTED.value,
            "at": datetime.datetime.now().isoformat(),
            "reason": f"Rejected: {reason}"
        })
        return curr

    def export_to_json(self) -> str:
        """Export all lessons in memory to a JSON string."""
        data = {lid: s.model_dump() for lid, s in self.lessons.items()}
        return json.dumps(data, indent=2)

    def import_from_json(self, json_str: str):
        """Load lessons from a previously exported JSON string."""
        raw = json.loads(json_str)
        loaded = {}
        for lid, s_dict in raw.items():
            loaded[lid] = LessonSession.model_validate(s_dict)
        self.lessons.update(loaded)
        if loaded:
            # Update next ID
            max_num = max([int(k.replace("lesson_", "")) for k in loaded.keys() if k.startswith("lesson_")] + [0])
            self._next_id = max_num + 1

# Singleton in-memory store for the app session
memory_store = MemoryLessonStore()
