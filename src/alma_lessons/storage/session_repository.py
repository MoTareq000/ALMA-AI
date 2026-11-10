import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import BaseModel, Field

from .mongo_client import get_mongo_db

logger = logging.getLogger(__name__)


class CheckpointLog(BaseModel):
    section_order: int
    selected_answer: str
    is_correct: bool
    detected_misconception: Optional[str] = None
    routed_to_remediation: bool = False
    answered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DialogueLog(BaseModel):
    section_order: int
    question: str
    spoken_answer: str
    asked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StudentSessionRecord(BaseModel):
    session_id: str
    student_id: str
    lesson_id: str
    current_section_order: int = 1
    personalized_greeting: Optional[str] = None
    checkpoint_logs: List[CheckpointLog] = Field(default_factory=list)
    dialogue_logs: List[DialogueLog] = Field(default_factory=list)
    status: str = Field(default="active", description="'active', 'completed', 'abandoned'")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class BaseSessionRepository:
    def create_session(
        self,
        session_id: str,
        student_id: str,
        lesson_id: str,
        personalized_greeting: Optional[str] = None
    ) -> StudentSessionRecord:
        raise NotImplementedError

    def get_session(self, session_id: str) -> Optional[StudentSessionRecord]:
        raise NotImplementedError

    def log_checkpoint(
        self,
        session_id: str,
        section_order: int,
        selected_answer: str,
        is_correct: bool,
        detected_misconception: Optional[str] = None,
        routed_to_remediation: bool = False
    ) -> Optional[StudentSessionRecord]:
        raise NotImplementedError

    def log_dialogue(
        self,
        session_id: str,
        section_order: int,
        question: str,
        spoken_answer: str
    ) -> Optional[StudentSessionRecord]:
        raise NotImplementedError

    def complete_session(self, session_id: str) -> Optional[StudentSessionRecord]:
        raise NotImplementedError


class MongoSessionRepository(BaseSessionRepository):
    """Persists runtime telemetry into ALMA's student_lesson_sessions collection."""

    def __init__(self):
        self.db = get_mongo_db()
        self.collection = self.db["student_lesson_sessions"] if self.db is not None else None
        self._local_cache: Dict[str, StudentSessionRecord] = {}

    def _sync_to_mongo(self, record: StudentSessionRecord):
        if self.collection is None:
            return
        doc = record.model_dump()
        doc["updated_at"] = datetime.now(timezone.utc)

        if record.student_id and ObjectId.is_valid(record.student_id):
            doc["student_id"] = ObjectId(record.student_id)

        try:
            self.collection.replace_one(
                {"session_id": record.session_id},
                doc,
                upsert=True
            )
        except Exception as e:
            logger.warning(f"Failed to persist student session {record.session_id} to Mongo: {e}")

    def create_session(
        self,
        session_id: str,
        student_id: str,
        lesson_id: str,
        personalized_greeting: Optional[str] = None
    ) -> StudentSessionRecord:
        record = StudentSessionRecord(
            session_id=session_id,
            student_id=student_id,
            lesson_id=lesson_id,
            personalized_greeting=personalized_greeting
        )
        self._local_cache[session_id] = record
        self._sync_to_mongo(record)
        return record

    def get_session(self, session_id: str) -> Optional[StudentSessionRecord]:
        if session_id in self._local_cache:
            return self._local_cache[session_id]

        if self.collection is not None:
            doc = self.collection.find_one({"session_id": session_id})
            if doc:
                clean = {k: (str(v) if isinstance(v, ObjectId) else v) for k, v in doc.items() if k != "_id"}
                record = StudentSessionRecord.model_validate(clean)
                self._local_cache[session_id] = record
                return record
        return None

    def log_checkpoint(
        self,
        session_id: str,
        section_order: int,
        selected_answer: str,
        is_correct: bool,
        detected_misconception: Optional[str] = None,
        routed_to_remediation: bool = False
    ) -> Optional[StudentSessionRecord]:
        record = self.get_session(session_id)
        if not record:
            return None

        log = CheckpointLog(
            section_order=section_order,
            selected_answer=selected_answer,
            is_correct=is_correct,
            detected_misconception=detected_misconception,
            routed_to_remediation=routed_to_remediation,
            answered_at=datetime.now(timezone.utc)
        )
        record.checkpoint_logs.append(log)
        if is_correct:
            record.current_section_order = section_order + 1
        record.updated_at = datetime.now(timezone.utc)
        self._sync_to_mongo(record)
        return record

    def log_dialogue(
        self,
        session_id: str,
        section_order: int,
        question: str,
        spoken_answer: str
    ) -> Optional[StudentSessionRecord]:
        record = self.get_session(session_id)
        if not record:
            return None

        log = DialogueLog(
            section_order=section_order,
            question=question,
            spoken_answer=spoken_answer,
            asked_at=datetime.now(timezone.utc)
        )
        record.dialogue_logs.append(log)
        record.updated_at = datetime.now(timezone.utc)
        self._sync_to_mongo(record)
        return record

    def complete_session(self, session_id: str) -> Optional[StudentSessionRecord]:
        record = self.get_session(session_id)
        if not record:
            return None

        record.status = "completed"
        record.completed_at = datetime.now(timezone.utc)
        record.updated_at = datetime.now(timezone.utc)
        self._sync_to_mongo(record)
        return record


class LocalSessionRepository(BaseSessionRepository):
    def __init__(self):
        self._sessions: Dict[str, StudentSessionRecord] = {}

    def create_session(
        self,
        session_id: str,
        student_id: str,
        lesson_id: str,
        personalized_greeting: Optional[str] = None
    ) -> StudentSessionRecord:
        record = StudentSessionRecord(
            session_id=session_id,
            student_id=student_id,
            lesson_id=lesson_id,
            personalized_greeting=personalized_greeting
        )
        self._sessions[session_id] = record
        return record

    def get_session(self, session_id: str) -> Optional[StudentSessionRecord]:
        return self._sessions.get(session_id)

    def log_checkpoint(
        self,
        session_id: str,
        section_order: int,
        selected_answer: str,
        is_correct: bool,
        detected_misconception: Optional[str] = None,
        routed_to_remediation: bool = False
    ) -> Optional[StudentSessionRecord]:
        record = self.get_session(session_id)
        if not record:
            return None
        record.checkpoint_logs.append(CheckpointLog(
            section_order=section_order,
            selected_answer=selected_answer,
            is_correct=is_correct,
            detected_misconception=detected_misconception,
            routed_to_remediation=routed_to_remediation
        ))
        if is_correct:
            record.current_section_order = section_order + 1
        return record

    def log_dialogue(
        self,
        session_id: str,
        section_order: int,
        question: str,
        spoken_answer: str
    ) -> Optional[StudentSessionRecord]:
        record = self.get_session(session_id)
        if not record:
            return None
        record.dialogue_logs.append(DialogueLog(
            section_order=section_order,
            question=question,
            spoken_answer=spoken_answer
        ))
        return record

    def complete_session(self, session_id: str) -> Optional[StudentSessionRecord]:
        record = self.get_session(session_id)
        if not record:
            return None
        record.status = "completed"
        record.completed_at = datetime.now(timezone.utc)
        return record

