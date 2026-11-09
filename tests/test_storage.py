# Tests for storage and versioning
from alma_lessons.domain import (
    LessonSpec,
    LessonContent,
    Section,
    Block,
    LessonState,
    DiagnosticQuestion,
    Segment,
    TopicSegmentation,
    LessonSegmentation,
)
from alma_lessons.storage import (
    MemoryLessonStore,
    session_repository,
    job_manager,
)
from alma_lessons.storage.mongo_lesson_store import _session_to_doc, _doc_to_session
from alma_lessons.storage.memory_store import LessonSession, LessonVersionRecord


def test_memory_store_lifecycle_and_json_export_import():
    store = MemoryLessonStore()

    spec = LessonSpec(
        topic="Recursion",
        programming_language="Python",
        learning_objectives=["Understand base case", "Recursive step"]
    )
    content_v1 = LessonContent(
        title="Recursion Basics",
        programming_language="Python",
        grade_level="Grade 11",
        introduction=[Block(type="paragraph", text="Intro")],
        objectives=["Understand base case"],
        sections=[
            Section(
                order=1,
                title="Base cases",
                purpose="stop recursion",
                covers_objectives=["Understand base case"],
                blocks=[Block(type="paragraph", text="A base case halts the recursive calls.")]
            )
        ],
        conclusion=[Block(type="paragraph", text="Conclusion")]
    )

    # 1. Create lesson session
    session = store.create_lesson(spec, content_v1, validation_report={"status": "PASSED"})
    assert session.lesson_id == "lesson_1"
    assert session.current_version_no == 1
    assert session.current_version.state == LessonState.AWAITING_REVIEW

    # 2. Teacher edit creates v2
    content_v2 = content_v1.model_copy(deep=True)
    content_v2.title = "Recursion Basics (Teacher Edited)"
    v2 = store.add_teacher_edit("lesson_1", content_v2)
    assert v2.version_no == 2
    assert session.current_version_no == 2
    assert len(session.versions) == 2

    # 3. Teacher approval
    approved_ver = store.approve_lesson("lesson_1", acknowledged_warnings=["Minor note"])
    assert approved_ver.state == LessonState.APPROVED
    assert "Minor note" in approved_ver.acknowledged_warnings

    # 4. JSON export and import verification
    exported_json = store.export_to_json()
    assert "lesson_1" in exported_json

    new_store = MemoryLessonStore()
    new_store.import_from_json(exported_json)
    assert "lesson_1" in new_store.lessons
    reloaded_session = new_store.lessons["lesson_1"]
    assert reloaded_session.current_version_no == 2
    assert reloaded_session.current_version.state == LessonState.APPROVED
    assert reloaded_session.current_version.content.title == "Recursion Basics (Teacher Edited)"


def test_mongo_schema_alignment_and_bidirectional_conversion():
    """Verify MongoDB document matches ALMA Lesson.model.js exactly and handles Mongoose documents."""
    spec = LessonSpec(
        topic="Python Dictionaries",
        programming_language="Python",
        grade_level="Grade 8",
        learning_objectives=["Key-value pairs", "dict.get() method"],
        target_duration_minutes=15
    )
    content = LessonContent(
        title="Mastering Python Dictionaries",
        programming_language="Python",
        grade_level="Grade 8",
        introduction=[Block(type="paragraph", text="Intro to dicts.")],
        objectives=["Key-value pairs"],
        sections=[
            Section(
                order=1,
                title="Keys and Values",
                purpose="Understand dict mapping",
                covers_objectives=["Key-value pairs"],
                blocks=[
                    Block(type="paragraph", text="Dicts store key-value associations."),
                    Block(type="code", language="python", code="d = {'a': 1}", expected_output="{'a': 1}")
                ],
                diagnostic_check=DiagnosticQuestion(
                    concept_tag="dict_keys",
                    question_text="Are dictionary keys unique?",
                    options=["Yes", "No"],
                    correct_answer="Yes",
                    misconception_map={"No": "Assumed duplicate keys are preserved"},
                    explanation="Dictionary keys must be unique and hashable."
                ),
                remediation_blocks=[Block(type="callout", callout_type="warning", text="Keys cannot be duplicated!")]
            )
        ],
        conclusion=[Block(type="paragraph", text="Dicts are fast!")]
    )
    segmentation = LessonSegmentation(
        lesson_title=content.title,
        total_segments=1,
        est_total_duration_minutes=0.8,
        topics=[TopicSegmentation(
            topic_title="Keys and Values",
            order=1,
            purpose="teach dicts",
            segments=[Segment(
                topic_title="Keys and Values",
                order_in_topic=1,
                order_in_lesson=1,
                title="Keys and Values - Part 1",
                narration_text="Dictionaries store data in key-value pairs.",
                word_count=7,
                est_seconds=45.0,
                attached_code="d = {'a': 1}"
            )]
        )]
    )

    session = LessonSession(
        lesson_id="lesson_99",
        spec=spec,
        current_version_no=1,
        versions=[LessonVersionRecord(
            version_no=1,
            source="generated",
            state=LessonState.AWAITING_REVIEW,
            content=content,
            segmentation=segmentation
        )]
    )

    # 1. Convert to Mongo Doc
    doc = _session_to_doc(session)

    # Verify top-level fields match Mongoose Lesson.model.js
    assert doc["topic"] == "Python Dictionaries"
    assert doc["programming_language"] == "Python"
    assert doc["grade_level"] == "Grade 8"
    assert doc["target_duration_minutes"] == 15
    assert doc["current_version_no"] == 1
    assert "versions" in doc
    assert len(doc["versions"]) == 1

    # Verify version 0 matches lessonVersionSchema
    v0 = doc["versions"][0]
    assert v0["version_no"] == 1
    assert v0["state"] == "AWAITING_REVIEW"
    assert v0["title"] == "Mastering Python Dictionaries"
    assert len(v0["introduction"]) == 1
    assert len(v0["sections"]) == 1
    assert len(v0["conclusion"]) == 1
    assert len(v0["segments"]) == 1
    assert v0["segments"][0]["order_in_lesson"] == 1
    assert v0["segments"][0]["attached_code"] == "d = {'a': 1}"

    # Verify section 0 diagnostic check
    s0 = v0["sections"][0]
    assert s0["diagnostic_check"]["concept_tag"] == "dict_keys"
    assert s0["diagnostic_check"]["correct_answer"] == "Yes"

    # 2. Convert pure Mongoose document (without python spec/content wrappers) back to LessonSession
    pure_mongoose_doc = {
        "_id": "60c72b2f9b1d8b2bad000001",
        "topic": "Functions in JavaScript",
        "programming_language": "JavaScript",
        "grade_level": "Grade 9",
        "target_duration_minutes": 20,
        "current_version_no": 1,
        "versions": [
            {
                "version_no": 1,
                "state": "APPROVED",
                "title": "Mastering JS Functions",
                "introduction": [{"type": "paragraph", "text": "Functions let you reuse code."}],
                "sections": [
                    {
                        "order": 1,
                        "title": "Declaring Functions",
                        "purpose": "Explain function keyword",
                        "covers_objectives": ["Write function declaration"],
                        "blocks": [{"type": "code", "language": "javascript", "code": "function add(a,b){return a+b;}"}],
                        "diagnostic_check": None,
                        "remediation_blocks": []
                    }
                ],
                "conclusion": [{"type": "paragraph", "text": "Great job with functions!"}],
                "segments": [
                    {
                        "order_in_lesson": 1,
                        "title": "Declaring Functions",
                        "narration_text": "Here is how you declare a function in JavaScript.",
                        "est_seconds": 45,
                        "attached_code": "function add(a,b){return a+b;}"
                    }
                ]
            }
        ]
    }
    reloaded = _doc_to_session(pure_mongoose_doc)
    assert reloaded.lesson_id == "60c72b2f9b1d8b2bad000001"
    assert reloaded.spec.topic == "Functions in JavaScript"
    assert reloaded.spec.programming_language == "JavaScript"
    assert reloaded.current_version.state == LessonState.APPROVED
    assert reloaded.current_version.content.title == "Mastering JS Functions"
    assert len(reloaded.current_version.content.sections) == 1
    assert reloaded.current_version.segmentation is not None
    assert reloaded.current_version.segmentation.total_segments == 1


def test_session_repository_and_job_manager():
    """Verify StudentLessonSession tracking and JobManager synchronization."""
    # Test Job Manager
    job = job_manager.create_job(
        topic="Object-Oriented Programming",
        programming_language="Python",
        grade_level="Grade 10",
        model="gemini-3.5-flash-lite"
    )
    assert job.topic == "Object-Oriented Programming"
    assert job.status == "pending"
    assert job.current_step == "queued"

    job_manager.update_progress(job.job_id, step="sections", progress=0.45, message="Generating sections...")
    updated_job = job_manager.get_job(job.job_id)
    assert updated_job.current_step == "sections"
    assert updated_job.progress_percent == 0.45

    job_manager.complete_job(job.job_id, lesson_id="lesson_99")
    completed_job = job_manager.get_job(job.job_id)
    assert completed_job.status == "completed"
    assert completed_job.lesson_id == "lesson_99"

    # Test Session Repository
    sess = session_repository.create_session(
        session_id="test_sess_001",
        student_id="student_mohamad_001",
        lesson_id="lesson_99",
        personalized_greeting="Hey Mohamad!"
    )
    assert sess.session_id == "test_sess_001"
    assert sess.current_section_order == 1

    # Log Checkpoint
    session_repository.log_checkpoint(
        session_id="test_sess_001",
        section_order=1,
        selected_answer="Yes",
        is_correct=True
    )
    sess_after_cp = session_repository.get_session("test_sess_001")
    assert len(sess_after_cp.checkpoint_logs) == 1
    assert sess_after_cp.checkpoint_logs[0].is_correct is True
    assert sess_after_cp.current_section_order == 2

    # Log Dialogue
    session_repository.log_dialogue(
        session_id="test_sess_001",
        section_order=1,
        question="What is a key?",
        spoken_answer="A key is an identifier in a dictionary."
    )
    sess_after_dlg = session_repository.get_session("test_sess_001")
    assert len(sess_after_dlg.dialogue_logs) == 1
    assert sess_after_dlg.dialogue_logs[0].question == "What is a key?"

    # Complete Session
    session_repository.complete_session("test_sess_001")
    sess_done = session_repository.get_session("test_sess_001")
    assert sess_done.status == "completed"
