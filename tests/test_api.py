import sys
from pathlib import Path

# Add src to sys.path so tests can import alma_lessons
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from fastapi.testclient import TestClient

from alma_lessons.main import app
from alma_lessons.domain import LessonSpec, LessonContent, Section, Block, DiagnosticQuestion
from alma_lessons.storage import memory_store, student_repository

client = TestClient(app)

def test_health_endpoint():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("online", "degraded")
    assert "database_adapter" in data

def test_student_profile_endpoint():
    # 1. Unknown student returns 404
    resp = client.get("/api/v1/runtime/students/non_existent_student_999")
    assert resp.status_code == 404

    # 2. Create student explicitly
    from alma_lessons.storage import StudentProfile, ConceptMasteryItem
    test_std = StudentProfile(
        student_id="test_student_001",
        first_name="Layla",
        last_name="Hassan",
        email="layla@alma.edu",
        student_code="STD-LAYLA-01",
        grade_level="Grade 7",
        school_name="ALMA Academy",
        current_streak=5,
        struggling_concepts=[
            ConceptMasteryItem(
                concept_id="python.loops",
                concept_label="Loop iteration",
                times_tested=4,
                times_correct=2,
                times_wrong=2
            )
        ]
    )
    student_repository.create_student(test_std)

    resp = client.get("/api/v1/runtime/students/test_student_001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["first_name"] == "Layla"
    assert data["grade_level"] == "Grade 7"
    assert len(data["struggling_concepts"]) >= 1

from unittest.mock import patch
from alma_lessons.llm.fake_client import FakeLLMClient

@patch("alma_lessons.api.routers.lessons.get_llm_client", return_value=FakeLLMClient())
def test_lessons_endpoints_crud_and_runtime(mock_llm=None):
    # 1. Create a lesson in memory store directly for testing
    spec = LessonSpec(
        topic="While Loops",
        programming_language="Python",
        grade_level="Grade 8",
        learning_objectives=["Understand while loop condition"]
    )
    content = LessonContent(
        title="While Loops in Python",
        programming_language="Python",
        grade_level="Grade 8",
        introduction=[Block(type="paragraph", text="Intro text")],
        objectives=["Understand while loop condition"],
        sections=[
            Section(
                order=1,
                title="While Loop Basics",
                purpose="teach while",
                covers_objectives=["Understand while loop condition"],
                blocks=[Block(type="paragraph", text="A while loop repeats while condition is True.")],
                diagnostic_check=DiagnosticQuestion(
                    question_text="What happens when condition is False?",
                    question_type="mcq",
                    options=["Loop ends", "Loop crashes", "Runs forever"],
                    correct_answer="Loop ends",
                    explanation="Loop terminates immediately.",
                    misconception_map={"Runs forever": "Confused False with True"}
                ),
                remediation_blocks=[Block(type="paragraph", text="Remember: False stops the loop!")]
            )
        ],
        conclusion=[Block(type="paragraph", text="Conclusion text")]
    )
    session = memory_store.create_lesson(spec=spec, content=content)

    # 2. Test GET /api/v1/lessons
    resp = client.get("/api/v1/lessons")
    assert resp.status_code == 200
    lessons = resp.json()
    assert len(lessons) >= 1
    assert any(l["lesson_id"] == session.lesson_id for l in lessons)

    # 3. Test GET /api/v1/lessons/{id}
    resp = client.get(f"/api/v1/lessons/{session.lesson_id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["lesson_id"] == session.lesson_id
    assert detail["current_version_no"] == 1
    assert detail["content"]["title"] == "While Loops in Python"

    # 4. Test Student Runtime: POST /api/v1/runtime/lessons/{id}/start
    # 4a. Unknown student returns 404
    resp = client.post(f"/api/v1/runtime/lessons/{session.lesson_id}/start", json={
        "student_id": "unknown_student_000"
    })
    assert resp.status_code == 404

    # 4b. Create student explicitly for session
    from alma_lessons.storage import StudentProfile
    rt_student = StudentProfile(
        student_id="student_runtime_001",
        first_name="Kareem",
        last_name="Adel",
        email="kareem@alma.edu",
        student_code="STD-KAREEM-01",
        grade_level="Grade 8",
        school_name="ALMA Academy",
        current_streak=4
    )
    student_repository.create_student(rt_student)

    resp = client.post(f"/api/v1/runtime/lessons/{session.lesson_id}/start", json={
        "student_id": "student_runtime_001"
    })
    assert resp.status_code == 200
    runtime_data = resp.json()
    assert "Kareem" in runtime_data["personalized_wrapper"]["prefix_audio_text"]
    assert runtime_data["student"]["first_name"] == "Kareem"

    # 5. Test Checkpoint Answer (Correct)
    resp = client.post(f"/api/v1/runtime/lessons/{session.lesson_id}/checkpoints/answer", json={
        "session_id": runtime_data["session_id"],
        "student_id": "student_runtime_001",
        "section_order": 1,
        "selected_option": "Loop ends"
    })
    assert resp.status_code == 200
    ans_data = resp.json()
    assert ans_data["is_correct"] is True
    assert ans_data["action"] == "CONTINUE"

    # 6. Test Checkpoint Answer (Incorrect with Misconception & Remediation)
    resp = client.post(f"/api/v1/runtime/lessons/{session.lesson_id}/checkpoints/answer", json={
        "session_id": runtime_data["session_id"],
        "student_id": "student_runtime_001",
        "section_order": 1,
        "selected_option": "Runs forever"
    })
    assert resp.status_code == 200
    ans_data = resp.json()
    assert ans_data["is_correct"] is False
    assert ans_data["action"] == "ROUTE_TO_REMEDIATION"
    assert "Confused False with True" in ans_data["detected_misconception"]
    assert len(ans_data["remediation_blocks"]) >= 1

    # 7. Test Ask ALMA
    resp = client.post(f"/api/v1/runtime/lessons/{session.lesson_id}/ask-alma", json={
        "session_id": runtime_data["session_id"],
        "student_id": "student_runtime_001",
        "current_section_order": 1,
        "question_text": "Why do while loops need an increment?"
    })
    assert resp.status_code == 200
    alma_data = resp.json()
    assert "Kareem" in alma_data["student_name"]
    assert len(alma_data["spoken_answer"]) > 0

    # 8. Test Teacher In-place Edit: PUT /api/v1/lessons/{id}/edit
    resp = client.put(f"/api/v1/lessons/{session.lesson_id}/edit", json={
        "title": "While Loops in Python (Edited Title)",
        "sections": [s.model_dump() for s in content.sections]
    })
    assert resp.status_code == 201
    edit_data = resp.json()
    assert edit_data["current_version_no"] == 2
    assert edit_data["content"]["title"] == "While Loops in Python (Edited Title)"

    # 9. Test Teacher Approve: POST /api/v1/lessons/{id}/approve
    resp = client.post(f"/api/v1/lessons/{session.lesson_id}/approve", json={
        "acknowledged_warnings": []
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"

    # 10. Test Runtime Session Telemetry: GET /api/v1/runtime/sessions/{session_id}
    resp = client.get(f"/api/v1/runtime/sessions/{runtime_data['session_id']}")
    assert resp.status_code == 200
    sess_doc = resp.json()
    assert sess_doc["session_id"] == runtime_data["session_id"]
    assert len(sess_doc["checkpoint_logs"]) == 2
    assert len(sess_doc["dialogue_logs"]) == 1

    # 11. Test Complete Lesson Session: POST /api/v1/runtime/lessons/{id}/complete
    resp = client.post(f"/api/v1/runtime/lessons/{session.lesson_id}/complete", json={
        "session_id": runtime_data["session_id"],
        "student_id": "student_runtime_001"
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    # 12. Test Lesson Generation Polling
    from alma_lessons.storage import job_manager
    test_job = job_manager.create_job(topic="Test Polling", programming_language="Python")
    resp = client.get(f"/api/v1/lesson-generations/job/{test_job.job_id}")
    assert resp.status_code == 200
    assert resp.json()["job_id"] == test_job.job_id


def test_api_key_auth_enforcement():
    from alma_lessons.config import config
    # Temporarily enforce authentication
    orig_disabled = config.alma_auth_disabled
    orig_keys = config.alma_api_keys
    try:
        config.alma_auth_disabled = False
        config.alma_api_keys = "secret-key-1,secret-key-2"

        # 1. Health endpoint requires no key
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

        # 2. Protected endpoint without key -> 401
        resp = client.get("/api/v1/lessons")
        assert resp.status_code == 401

        # 3. Protected endpoint with invalid key -> 401
        resp = client.get("/api/v1/lessons", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 401

        # 4. Protected endpoint with valid key -> 200
        resp = client.get("/api/v1/lessons", headers={"X-API-Key": "secret-key-1"})
        assert resp.status_code == 200
    finally:
        config.alma_auth_disabled = orig_disabled
        config.alma_api_keys = orig_keys


def test_curriculum_upload_security():
    # 1. File without %PDF magic bytes -> 400
    fake_pdf = b"NOT_A_REAL_PDF_CONTENT"
    resp = client.post(
        "/api/v1/curriculum/extract",
        files={"file": ("fake.pdf", fake_pdf, "application/pdf")}
    )
    assert resp.status_code == 400
    assert "magic bytes" in resp.json()["detail"].lower()

    # 2. Oversized file exceeding MAX_UPLOAD_MB -> 413
    from alma_lessons.config import config
    orig_mb = config.max_upload_mb
    try:
        config.max_upload_mb = 1  # 1 MB
        oversized = b"%PDF-1.4 " + (b"0" * (1024 * 1024 + 100))
        resp = client.post(
            "/api/v1/curriculum/extract",
            files={"file": ("large.pdf", oversized, "application/pdf")}
        )
        assert resp.status_code == 413
        assert "exceeds maximum upload size" in resp.json()["detail"]
    finally:
        config.max_upload_mb = orig_mb


if __name__ == "__main__":
    print("Running test_health_endpoint...")
    test_health_endpoint()
    print("Running test_student_profile_endpoint...")
    test_student_profile_endpoint()
    print("Running test_lessons_endpoints_crud_and_runtime...")
    test_lessons_endpoints_crud_and_runtime()
    print("[OK] All API tests passed successfully!")
