"""End-to-End Smoke Test for ALMA AI Ecosystem.

Validates that FastAPI, MongoDB, and Redis (when active) operate end-to-end:
1. Connects using URI from config.
2. Creates isolated test student and lesson through the domain/store.
3. Tests runtime session, checkpoint answers, dialogue, and job tracking via FastAPI endpoints.
4. Cleans up all created test documents.
5. Skips gracefully if MongoDB or Redis are unreachable.

Can be run locally or via Docker Compose:
    docker compose --profile test run --rm smoke-test
"""

import sys
import time
from pathlib import Path

# Add src to pythonpath
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pymongo import MongoClient
from fastapi.testclient import TestClient

from alma_lessons.config import config
from alma_lessons.main import app
from alma_lessons.domain import (
    LessonContent,
    LessonSpec,
    Section,
    Block,
    DiagnosticQuestion,
)
from alma_lessons.storage import memory_store, student_repository, job_manager


def run_e2e_smoke_test() -> int:
    print("==================================================")
    print("   ALMA ACADEMY END-TO-END SMOKE TEST SUITE       ")
    print("==================================================")

    # 1. Connectivity Check: MongoDB
    print("\n[Step 1/5] Checking MongoDB Connectivity...")
    mongo_uri = config.mongodb_uri or "mongodb://localhost:27017"
    db_name = config.mongodb_db_name or "alma_lessons"

    try:
        mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        mongo_client.admin.command("ping")
        db = mongo_client[db_name]
        print(f" -> Connected to MongoDB at {mongo_uri} (db: '{db_name}').")
    except Exception as err:
        print(f"\n[SKIPPED] MongoDB is unreachable at {mongo_uri}: {err}")
        print("Smoke test skipped because external database is not running.")
        return 0

    # Connectivity Check: Redis (if RQ backend configured)
    if config.job_backend == "rq":
        print("Checking Redis Connectivity for RQ...")
        try:
            import redis
            r_client = redis.Redis.from_url(config.redis_url, socket_timeout=2)
            r_client.ping()
            print(f" -> Connected to Redis at {config.redis_url}.")
        except Exception as err:
            print(f"\n[SKIPPED] Redis is unreachable at {config.redis_url}: {err}")
            print("Smoke test skipped because Redis is required when JOB_BACKEND=rq.")
            return 0

    # Headers for auth
    headers = {}
    if not config.alma_auth_disabled and config.alma_api_keys:
        headers["X-API-Key"] = config.alma_api_keys[0]

    test_client = TestClient(app)

    # Unique test IDs for total isolation
    timestamp_id = int(time.time() * 1000)
    test_lesson_id = f"smoke_lesson_{timestamp_id}"
    test_student_id = f"smoke_student_{timestamp_id}"
    created_session_id = None
    created_job_id = None

    try:
        # 2. Setup isolated test student and lesson
        print("\n[Step 2/5] Creating isolated test student and lesson...")
        student_repository.create_student({
            "student_id": test_student_id,
            "first_name": "Smoke",
            "last_name": "Student",
            "email": f"{test_student_id}@alma.test",
            "student_code": f"STD-{test_student_id}",
            "grade_level": "Grade 7",
        })
        print(f" -> Created student '{test_student_id}'.")

        test_spec = LessonSpec(
            subject="Programming",
            topic="Smoke Test For Loops",
            programming_language="Python",
            grade_level="Grade 7",
            learning_objectives=["Understand for loops", "Trace iterations"],
            target_duration_minutes=10,
        )

        test_content = LessonContent(
            title="Smoke Test For Loops Lesson",
            programming_language="Python",
            grade_level="Grade 7",
            target_duration_minutes=10,
            introduction=[Block(type="paragraph", text="Welcome to the smoke test lesson.")],
            objectives=["Understand for loops", "Trace iterations"],
            sections=[
                Section(
                    order=1,
                    title="Introduction to For Loops",
                    purpose="Explain loop basics",
                    covers_objectives=["Understand for loops"],
                    blocks=[
                        Block(type="paragraph", text="For loops repeat actions over a sequence."),
                        Block(type="code", language="python", code="for i in range(3):\n    print(i)"),
                    ],
                    diagnostic_check=DiagnosticQuestion(
                        question_text="What does range(3) produce?",
                        options=["0, 1, 2", "1, 2, 3", "0, 1, 2, 3"],
                        correct_answer="0, 1, 2",
                        explanation="range(3) generates numbers 0, 1, and 2.",
                    ),
                )
            ],
            conclusion=[Block(type="paragraph", text="Great job completing the smoke test lesson.")],
        )

        saved_session = memory_store.create_lesson(
            spec=test_spec,
            content=test_content,
        )
        test_lesson_id = saved_session.lesson_id
        memory_store.approve_lesson(test_lesson_id, acknowledged_warnings=[])
        print(f" -> Created and approved lesson '{test_lesson_id}'.")

        # 3. Test API Health & Lesson retrieval
        print("\n[Step 3/5] Testing API health and lesson endpoints...")
        r = test_client.get("/api/v1/health")
        assert r.status_code == 200, f"Health check failed: {r.text}"
        health_data = r.json()
        print(f" -> GET /api/v1/health: 200 OK (Status: {health_data.get('status')}, DB: {health_data.get('database_adapter')})")

        r = test_client.get(f"/api/v1/lessons/{test_lesson_id}", headers=headers)
        assert r.status_code == 200, f"Get lesson failed: {r.text}"
        assert r.json()["lesson_id"] == test_lesson_id
        print(f" -> GET /api/v1/lessons/{test_lesson_id}: 200 OK")

        # 4. Test Student Runtime & Telemetry
        print("\n[Step 4/5] Testing student runtime session and telemetry...")
        r = test_client.post(
            f"/api/v1/runtime/lessons/{test_lesson_id}/start",
            json={"student_id": test_student_id},
            headers=headers,
        )
        assert r.status_code == 200, f"Start session failed: {r.text}"
        start_res = r.json()
        created_session_id = start_res["session_id"]
        print(f" -> POST /runtime/lessons/.../start: 200 OK (Session ID: {created_session_id})")

        # Submit Checkpoint Answer
        r = test_client.post(
            f"/api/v1/runtime/lessons/{test_lesson_id}/checkpoints/answer",
            json={
                "session_id": created_session_id,
                "student_id": test_student_id,
                "section_order": 1,
                "selected_option": "0, 1, 2",
            },
            headers=headers,
        )
        assert r.status_code == 200, f"Checkpoint answer failed: {r.text}"
        print(" -> POST /runtime/lessons/.../checkpoints/answer: 200 OK")

        # Ask ALMA
        r = test_client.post(
            f"/api/v1/runtime/lessons/{test_lesson_id}/ask-alma",
            json={
                "session_id": created_session_id,
                "student_id": test_student_id,
                "current_section_order": 1,
                "question_text": "What is a loop variable?",
            },
            headers=headers,
        )
        assert r.status_code == 200, f"Ask ALMA failed: {r.text}"
        print(" -> POST /runtime/lessons/.../ask-alma: 200 OK")

        # Verify session state via API
        r = test_client.get(f"/api/v1/runtime/sessions/{created_session_id}", headers=headers)
        assert r.status_code == 200
        sess_data = r.json()
        assert len(sess_data["checkpoint_logs"]) >= 1
        assert len(sess_data["dialogue_logs"]) >= 1
        print(" -> Verified telemetry logs recorded in session.")

        # Complete Session
        r = test_client.post(
            f"/api/v1/runtime/lessons/{test_lesson_id}/complete",
            json={"session_id": created_session_id, "student_id": test_student_id},
            headers=headers,
        )
        assert r.status_code == 200
        print(" -> POST /runtime/lessons/.../complete: 200 OK")

        # 5. Test Job Manager & Tracking
        print("\n[Step 5/5] Testing Job Manager & Status Tracking...")
        job = job_manager.create_job(
            topic="Smoke Test Job",
            programming_language="Python",
            grade_level="Grade 7",
        )
        created_job_id = job.job_id
        job_manager.update_progress(created_job_id, step="synthesizing", progress=0.8, message="Verifying smoke test")
        job_manager.complete_job(created_job_id, lesson_id=test_lesson_id)

        r = test_client.get(f"/api/v1/lesson-generations/job/{created_job_id}", headers=headers)
        assert r.status_code == 200
        assert r.json()["status"] == "completed"
        print(f" -> Job {created_job_id} completed and polled successfully.")

        print("\n==================================================")
        print("   ALL 5 SMOKE TEST STEPS PASSED SUCCESSFULLY!    ")
        print("==================================================")
        return 0

    finally:
        # Cleanup
        print("\nCleaning up test records from database...")
        try:
            if created_session_id:
                db["student_lesson_sessions"].delete_one({"session_id": created_session_id})
            db["students"].delete_one({"student_id": test_student_id})
            db["students"].delete_one({"student_code": f"STD-{test_student_id}"})
            db["lessons"].delete_one({"lesson_id": test_lesson_id})
            if hasattr(memory_store, "lessons") and test_lesson_id in memory_store.lessons:
                del memory_store.lessons[test_lesson_id]
            if hasattr(memory_store, "_cache") and test_lesson_id in memory_store._cache:
                del memory_store._cache[test_lesson_id]
            if created_job_id:
                db["lesson_generations"].delete_one({"job_id": created_job_id})
            print(" -> Cleanup complete. No residual test data left.")
        except Exception as cleanup_err:
            print(f" -> Warning during cleanup: {cleanup_err}")
        finally:
            mongo_client.close()


if __name__ == "__main__":
    exit_code = run_e2e_smoke_test()
    sys.exit(exit_code)
