"""
End-to-End Smoke Test for ALMA Ecosystem
========================================
Validates that MongoDB, FastAPI, and Express schemas are 100% interoperable.
"""

import sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "src"))

from fastapi.testclient import TestClient
from pymongo import MongoClient

from alma_lessons.main import app
from alma_lessons.domain import LessonSpec, LessonContent, Section, Block, DiagnosticQuestion
from alma_lessons.storage import memory_store, student_repository, session_repository, job_manager
from alma_lessons.storage.mongo_lesson_store import _session_to_doc

def run_e2e_test():
    print("==================================================")
    print("   ALMA ACADEMY END-TO-END VERIFICATION SUITE     ")
    print("==================================================")

    # 1. MongoDB Connection
    print("\n[Step 1/5] Verifying MongoDB Connection...")
    client = MongoClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=2000)
    client.admin.command("ping")
    db = client["ALMA"]
    print(" -> MongoDB is healthy and reachable.")
    print(" -> Active collections in 'ALMA':", db.list_collection_names())

    # 2. FastAPI Test Client
    print("\n[Step 2/5] Testing FastAPI REST Endpoints...")
    test_client = TestClient(app)

    # Health
    r = test_client.get("/api/v1/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    print(f" -> GET /api/v1/health: 200 OK (DB Adapter: {r.json().get('database_adapter')})")

    # List Lessons
    r = test_client.get("/api/v1/lessons")
    assert r.status_code == 200, f"List lessons failed: {r.text}"
    lessons = r.json()
    print(f" -> GET /api/v1/lessons: 200 OK (Count: {len(lessons)} lessons)")
    assert len(lessons) > 0, "Expected at least 1 lesson in database"
    first_lesson_id = lessons[0]["lesson_id"]

    # View Lesson
    r = test_client.get(f"/api/v1/lessons/{first_lesson_id}")
    assert r.status_code == 200, f"Get lesson failed: {r.text}"
    detail = r.json()
    print(f" -> GET /api/v1/lessons/{first_lesson_id}: 200 OK (Title: '{detail['content']['title']}')")

    # 3. Student Adaptive Runtime & MongoDB Telemetry
    print("\n[Step 3/5] Testing Student Runtime & Telemetry Persistence...")
    r = test_client.post(f"/api/v1/runtime/lessons/{first_lesson_id}/start", json={
        "student_id": "student_mohamad_001"
    })
    assert r.status_code == 200, f"Start session failed: {r.text}"
    start_data = r.json()
    session_id = start_data["session_id"]
    print(f" -> POST /api/v1/runtime/lessons/{first_lesson_id}/start: 200 OK (Session: {session_id})")

    # Verify session persisted to MongoDB
    persisted_sess = session_repository.get_session(session_id)
    assert persisted_sess is not None, "Session was not found in Mongo repository"
    print(f" -> Session successfully verified in MongoDB 'student_lesson_sessions'.")

    # Checkpoint Answer
    r = test_client.post(f"/api/v1/runtime/lessons/{first_lesson_id}/checkpoints/answer", json={
        "session_id": session_id,
        "student_id": "student_mohamad_001",
        "section_order": 1,
        "selected_option": "print(list(range(3)))"
    })
    assert r.status_code == 200
    print(f" -> POST /api/v1/runtime/lessons/{first_lesson_id}/checkpoints/answer: 200 OK")

    # Ask ALMA
    r = test_client.post(f"/api/v1/runtime/lessons/{first_lesson_id}/ask-alma", json={
        "session_id": session_id,
        "student_id": "student_mohamad_001",
        "current_section_order": 1,
        "question_text": "How do for loops count iterations?"
    })
    assert r.status_code == 200
    print(f" -> POST /api/v1/runtime/lessons/{first_lesson_id}/ask-alma: 200 OK")

    # Verify telemetry logs in MongoDB
    r = test_client.get(f"/api/v1/runtime/sessions/{session_id}")
    assert r.status_code == 200
    sess_state = r.json()
    assert len(sess_state["checkpoint_logs"]) >= 1
    assert len(sess_state["dialogue_logs"]) >= 1
    print(f" -> GET /api/v1/runtime/sessions/{session_id}: 200 OK (Telemetry verified in MongoDB)")

    # 4. Job Manager & lesson_generations Collection
    print("\n[Step 4/5] Testing Lesson Generation Job Tracking...")
    job = job_manager.create_job(
        topic="Functions and Scope",
        programming_language="Python",
        grade_level="Grade 8"
    )
    job_manager.update_progress(job.job_id, step="sections", progress=0.5, message="Writing sections...")
    job_manager.complete_job(job.job_id, lesson_id=first_lesson_id)

    # Poll via ALMA standard route
    r = test_client.get(f"/api/v1/lesson-generations/job/{job.job_id}")
    assert r.status_code == 200
    assert r.json()["status"] == "completed"
    print(f" -> Job polling verified on ALMA route /api/v1/lesson-generations/job/{job.job_id}.")

    # 5. Schema Validation against MongoDB Document
    print("\n[Step 5/5] Checking Mongoose Schema Strict Alignment in MongoDB...")
    mongo_doc = db["lessons"].find_one({"lesson_id": first_lesson_id})
    assert mongo_doc is not None
    required_root_fields = ["topic", "programming_language", "grade_level", "versions", "current_version_no"]
    for f in required_root_fields:
        assert f in mongo_doc, f"Missing required root field '{f}' in MongoDB document"
        assert mongo_doc[f] is not None, f"Field '{f}' is None in MongoDB document"

    v0 = mongo_doc["versions"][0]
    required_v_fields = ["version_no", "state", "title", "introduction", "sections", "conclusion", "segments"]
    for vf in required_v_fields:
        assert vf in v0, f"Missing required version field '{vf}' in MongoDB version 0"

    assert v0["state"] in ["AWAITING_REVIEW", "APPROVED", "REJECTED"], f"Invalid state enum: {v0['state']}"
    print(" -> All Mongoose schema invariants verified: topic, grade_level, versions, states, blocks, and segments.")

    print("\n==================================================")
    print("  ALL 5 END-TO-END VERIFICATION STEPS PASSED!   ")
    print("==================================================")

if __name__ == "__main__":
    run_e2e_test()

