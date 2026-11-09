import json
import logging
import datetime
from typing import Dict, List, Optional, Any
from bson import ObjectId

from ..domain import (
    LessonSpec,
    LessonContent,
    LessonState,
    LessonSegmentation,
    TopicSegmentation,
    Segment,
    Section,
    Block,
    DiagnosticQuestion,
)
from .memory_store import LessonVersionRecord, LessonSession
from .mongo_client import get_mongo_db

logger = logging.getLogger(__name__)


def _session_to_doc(session: LessonSession) -> Dict[str, Any]:
    """Convert LessonSession to a MongoDB document adhering 100% to ALMA Lesson.model.js Mongoose schema."""
    spec_dict = session.spec.model_dump()
    topic = session.spec.topic
    programming_language = session.spec.programming_language
    grade_level = session.spec.grade_level
    target_duration_minutes = session.spec.target_duration_minutes or 15

    course_id = None
    if getattr(session.spec, "course_id", None):
        cid = session.spec.course_id
        course_id = ObjectId(cid) if ObjectId.is_valid(cid) else cid

    module_id = None
    if getattr(session.spec, "module_id", None):
        mid = session.spec.module_id
        module_id = ObjectId(mid) if ObjectId.is_valid(mid) else mid

    created_by = None
    if getattr(session.spec, "created_by", None):
        cb = session.spec.created_by
        created_by = ObjectId(cb) if ObjectId.is_valid(cb) else cb

    versions_doc = []
    for v in session.versions:
        intro_blocks = [b.model_dump(exclude_none=True) for b in v.content.introduction]
        concl_blocks = [b.model_dump(exclude_none=True) for b in v.content.conclusion]

        sections_doc = []
        for s in v.content.sections:
            diag_dict = None
            if s.diagnostic_check:
                diag_dict = {
                    "concept_tag": getattr(s.diagnostic_check, "concept_tag", None),
                    "question_text": s.diagnostic_check.question_text,
                    "code_snippet": s.diagnostic_check.code_snippet,
                    "options": s.diagnostic_check.options,
                    "correct_answer": s.diagnostic_check.correct_answer,
                    "misconception_map": s.diagnostic_check.misconception_map or {},
                    "explanation": s.diagnostic_check.explanation,
                }

            sec_dict = {
                "order": s.order,
                "title": s.title,
                "purpose": s.purpose,
                "covers_objectives": s.covers_objectives,
                "blocks": [b.model_dump(exclude_none=True) for b in s.blocks],
                "diagnostic_check": diag_dict,
                "remediation_blocks": [b.model_dump(exclude_none=True) for b in s.remediation_blocks],
            }
            sections_doc.append(sec_dict)

        # Flatten segments for Mongoose speechSegmentSchema
        segments_doc = []
        if v.segmentation and v.segmentation.topics:
            for top in v.segmentation.topics:
                for seg in top.segments:
                    segments_doc.append({
                        "order_in_lesson": seg.order_in_lesson,
                        "title": seg.title,
                        "narration_text": seg.narration_text,
                        "est_seconds": int(round(seg.est_seconds)),
                        "attached_code": seg.attached_code
                    })

        state_val = v.state.value if hasattr(v.state, "value") else str(v.state)
        if "approv" in state_val.lower():
            state_enum = "APPROVED"
        elif "reject" in state_val.lower():
            state_enum = "REJECTED"
        else:
            state_enum = "AWAITING_REVIEW"

        v_dict = {
            "version_no": v.version_no,
            "state": state_enum,
            "title": v.content.title,
            "introduction": intro_blocks,
            "sections": sections_doc,
            "conclusion": concl_blocks,
            "segments": segments_doc,
            "teacher_feedback": v.teacher_feedback,
            "created_at": v.created_at,
            # Preserved engine fields for lossless pipeline roundtrips
            "source": v.source,
            "validation_report": v.validation_report,
            "segmentation": v.segmentation.model_dump() if v.segmentation else None,
            "puzzles": [p.model_dump() for p in v.content.puzzles],
            "exercises": [e.model_dump() for e in v.content.exercises],
            "content": v.content.model_dump(),
        }
        versions_doc.append(v_dict)

    doc = {
        "lesson_id": session.lesson_id,
        "course_id": course_id,
        "module_id": module_id,
        "topic": topic,
        "programming_language": programming_language,
        "grade_level": grade_level,
        "target_duration_minutes": target_duration_minutes,
        "current_version_no": session.current_version_no,
        "approved_version_no": session.approved_version_no,
        "created_by": created_by,
        "versions": versions_doc,
        "spec": spec_dict,
        "status_history": session.status_history,
        "created_at": session.created_at,
        "updated_at": datetime.datetime.utcnow(),
    }
    return doc


def _doc_to_session(doc: Dict[str, Any]) -> LessonSession:
    """Parse a MongoDB document (created either by FastAPI or ALMA Express) into a robust LessonSession."""
    lesson_id = doc.get("lesson_id") or str(doc.get("_id"))

    # Parse or reconstruct LessonSpec
    if "spec" in doc and isinstance(doc["spec"], dict):
        spec = LessonSpec.model_validate(doc["spec"])
    else:
        objectives = []
        for v in doc.get("versions", []):
            for sec in v.get("sections", []):
                for obj in sec.get("covers_objectives", []):
                    if obj not in objectives:
                        objectives.append(obj)
        if not objectives:
            objectives = [f"Understand and apply {doc.get('topic', 'core programming concepts')}"]

        course_id_raw = doc.get("course_id")
        module_id_raw = doc.get("module_id")
        created_by_raw = doc.get("created_by")

        spec = LessonSpec(
            topic=doc.get("topic", "Programming Lesson"),
            programming_language=doc.get("programming_language", "Python"),
            grade_level=doc.get("grade_level", "Grade 8"),
            target_duration_minutes=doc.get("target_duration_minutes", 15),
            learning_objectives=objectives,
            course_id=str(course_id_raw) if course_id_raw else None,
            module_id=str(module_id_raw) if module_id_raw else None,
            created_by=str(created_by_raw) if created_by_raw else None,
        )

    # Parse versions
    versions: List[LessonVersionRecord] = []
    raw_versions = doc.get("versions", [])
    for v_dict in raw_versions:
        v_no = v_dict.get("version_no", len(versions) + 1)
        raw_state = str(v_dict.get("state", "AWAITING_REVIEW")).upper()
        if "APPROV" in raw_state:
            state = LessonState.APPROVED
        elif "REJECT" in raw_state:
            state = LessonState.REJECTED
        else:
            state = LessonState.AWAITING_REVIEW
        source = v_dict.get("source", "generated")

        # Parse content
        if "content" in v_dict and isinstance(v_dict["content"], dict):
            content = LessonContent.model_validate(v_dict["content"])
        else:
            intro = [Block.model_validate(b) for b in v_dict.get("introduction", [])]
            concl = [Block.model_validate(b) for b in v_dict.get("conclusion", [])]
            sections = []
            for s in v_dict.get("sections", []):
                blocks = [Block.model_validate(b) for b in s.get("blocks", [])]
                remed = [Block.model_validate(b) for b in s.get("remediation_blocks", [])]
                diag = None
                if s.get("diagnostic_check"):
                    d_raw = s["diagnostic_check"]
                    diag = DiagnosticQuestion(
                        concept_tag=d_raw.get("concept_tag"),
                        question_text=d_raw.get("question_text", ""),
                        code_snippet=d_raw.get("code_snippet"),
                        options=d_raw.get("options", []),
                        correct_answer=d_raw.get("correct_answer", ""),
                        misconception_map=d_raw.get("misconception_map", {}),
                        explanation=d_raw.get("explanation", ""),
                    )
                sections.append(Section(
                    order=s.get("order", len(sections) + 1),
                    title=s.get("title", f"Section {len(sections) + 1}"),
                    purpose=s.get("purpose", ""),
                    covers_objectives=s.get("covers_objectives", []),
                    blocks=blocks,
                    diagnostic_check=diag,
                    remediation_blocks=remed
                ))

            content = LessonContent(
                title=v_dict.get("title", spec.topic),
                programming_language=spec.programming_language,
                grade_level=spec.grade_level,
                target_duration_minutes=spec.target_duration_minutes,
                introduction=intro,
                objectives=spec.learning_objectives,
                sections=sections,
                conclusion=concl
            )

        # Parse segmentation
        segmentation = None
        if "segmentation" in v_dict and v_dict["segmentation"]:
            try:
                segmentation = LessonSegmentation.model_validate(v_dict["segmentation"])
            except Exception:
                pass

        if not segmentation and "segments" in v_dict and v_dict["segments"]:
            seg_list = []
            for sg in v_dict["segments"]:
                seg_list.append(Segment(
                    topic_title=content.title,
                    order_in_topic=sg.get("order_in_lesson", len(seg_list) + 1),
                    order_in_lesson=sg.get("order_in_lesson", len(seg_list) + 1),
                    title=sg.get("title", f"Part {len(seg_list) + 1}"),
                    narration_text=sg.get("narration_text", ""),
                    word_count=len(sg.get("narration_text", "").split()),
                    est_seconds=float(sg.get("est_seconds", 45)),
                    attached_code=sg.get("attached_code")
                ))
            top_seg = TopicSegmentation(
                topic_title=content.title,
                order=1,
                purpose=spec.topic,
                segments=seg_list
            )
            segmentation = LessonSegmentation(
                lesson_title=content.title,
                total_segments=len(seg_list),
                est_total_duration_minutes=sum(s.est_seconds for s in seg_list) / 60.0,
                topics=[top_seg]
            )

        v_rec = LessonVersionRecord(
            version_no=v_no,
            source=source,
            state=state,
            content=content,
            validation_report=v_dict.get("validation_report"),
            segmentation=segmentation,
            teacher_feedback=v_dict.get("teacher_feedback"),
            rejection_reason=v_dict.get("rejection_reason"),
            acknowledged_warnings=v_dict.get("acknowledged_warnings", []),
            created_at=str(v_dict.get("created_at") or datetime.datetime.now().isoformat())
        )
        versions.append(v_rec)

    session = LessonSession(
        lesson_id=lesson_id,
        spec=spec,
        current_version_no=doc.get("current_version_no", len(versions) or 1),
        created_at=str(doc.get("created_at") or datetime.datetime.now().isoformat()),
        versions=versions,
        status_history=doc.get("status_history", [])
    )
    return session


class MongoLessonStore:
    """MongoDB-backed store for managing lessons, version history, and state transitions.
    Fully aligned with ALMA Mongoose schemas (Lesson.model.js) and compatible with Express repositories.
    """

    def __init__(self):
        self.db = get_mongo_db()
        self.collection = self.db["lessons"] if self.db is not None else None
        self._cache: Dict[str, LessonSession] = {}
        self._next_id = 1
        self._load_from_db()

    def _load_from_db(self):
        if self.collection is None:
            return
        try:
            for doc in self.collection.find():
                try:
                    session = _doc_to_session(doc)
                    self._cache[session.lesson_id] = session

                    # Track numerical IDs like lesson_1, lesson_2
                    lid = session.lesson_id
                    if lid.startswith("lesson_"):
                        try:
                            num = int(lid.replace("lesson_", ""))
                            if num >= self._next_id:
                                self._next_id = num + 1
                        except ValueError:
                            pass
                except Exception as e:
                    logger.warning(f"Error parsing lesson document {doc.get('_id')} from Mongo: {e}")

            logger.info(f"Loaded {len(self._cache)} lessons from MongoDB 'lessons' collection.")
        except Exception as e:
            logger.error(f"Failed to load lessons from MongoDB: {e}")

    def _persist(self, session: LessonSession):
        """Save a lesson session to MongoDB using unified Mongoose document structure."""
        self._cache[session.lesson_id] = session
        if self.collection is not None:
            try:
                doc = _session_to_doc(session)

                # Search filter: match either lesson_id or _id if it's an ObjectId
                filt = {"lesson_id": session.lesson_id}
                if ObjectId.is_valid(session.lesson_id):
                    filt = {"$or": [{"lesson_id": session.lesson_id}, {"_id": ObjectId(session.lesson_id)}]}

                self.collection.replace_one(
                    filt,
                    doc,
                    upsert=True
                )
            except Exception as e:
                logger.error(f"Failed to persist lesson {session.lesson_id} to MongoDB: {e}")

    @property
    def lessons(self) -> Dict[str, LessonSession]:
        return self._cache

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
        self._persist(session)
        return session

    def add_teacher_edit(
        self,
        lesson_id: str,
        edited_content: LessonContent,
        revalidation_report: Optional[Dict[str, Any]] = None,
        segmentation: Optional[LessonSegmentation] = None,
    ) -> LessonVersionRecord:
        session = self._cache.get(lesson_id)
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
        self._persist(session)
        return new_version

    def add_regeneration(
        self,
        lesson_id: str,
        new_content: LessonContent,
        feedback: str,
        validation_report: Optional[Dict[str, Any]] = None
    ) -> LessonVersionRecord:
        session = self._cache.get(lesson_id)
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
        self._persist(session)
        return new_version

    def approve_lesson(
        self,
        lesson_id: str,
        acknowledged_warnings: List[str],
        segmentation: Optional[LessonSegmentation] = None
    ) -> LessonVersionRecord:
        session = self._cache.get(lesson_id)
        if not session:
            raise KeyError(f"Lesson not found: {lesson_id}")

        curr = session.current_version
        if not curr:
            raise ValueError("No active version found")

        curr.state = LessonState.APPROVED
        curr.acknowledged_warnings = acknowledged_warnings
        if segmentation:
            curr.segmentation = segmentation

        session.status_history.append({
            "from": LessonState.AWAITING_REVIEW.value,
            "to": LessonState.APPROVED.value,
            "at": datetime.datetime.now().isoformat(),
            "reason": "Approved by teacher"
        })
        self._persist(session)
        return curr

    def reject_lesson(self, lesson_id: str, reason: str) -> LessonVersionRecord:
        session = self._cache.get(lesson_id)
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
        self._persist(session)
        return curr

    def export_to_json(self) -> str:
        data = {lid: s.model_dump() for lid, s in self._cache.items()}
        return json.dumps(data, indent=2)

    def import_from_json(self, json_str: str):
        raw = json.loads(json_str)
        loaded = {}
        for lid, s_dict in raw.items():
            loaded[lid] = LessonSession.model_validate(s_dict)
            self._persist(loaded[lid])
