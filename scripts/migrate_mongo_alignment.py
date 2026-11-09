"""
Migration Script: Align MongoDB collections with ALMA schema
============================================================
Updates existing documents in 'lessons' and syncs 'lesson_jobs' to 'lesson_generations'.
"""

import sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "src"))

from alma_lessons.storage.mongo_client import get_mongo_db
from alma_lessons.storage.mongo_lesson_store import _doc_to_session, _session_to_doc

def run_migration():
    db = get_mongo_db()
    if db is None:
        print("MongoDB is not connected. Nothing to migrate.")
        return

    lessons_col = db["lessons"]
    migrated_lessons = 0
    for doc in list(lessons_col.find()):
        try:
            sess = _doc_to_session(doc)
            updated_doc = _session_to_doc(sess)
            lessons_col.replace_one({"_id": doc["_id"]}, updated_doc)
            migrated_lessons += 1
            print(f"[OK] Migrated lesson: {sess.lesson_id} - topic: '{sess.spec.topic}'")
        except Exception as e:
            print(f"[ERROR] Failed to migrate doc {doc.get('_id')}: {e}")
    print(f"Total lessons migrated: {migrated_lessons}")

    # Migrate jobs to lesson_generations
    if "lesson_jobs" in db.list_collection_names():
        jobs_col = db["lesson_jobs"]
        gen_col = db["lesson_generations"]
        job_count = 0
        for jdoc in jobs_col.find():
            meta = jdoc.get("metadata", {})
            gen_doc = {
                "job_id": jdoc.get("job_id"),
                "lesson_id": jdoc.get("lesson_id"),
                "topic": meta.get("topic") or "Python Programming",
                "programming_language": meta.get("language") or "Python",
                "grade_level": meta.get("grade_level") or "Grade 8",
                "model": meta.get("model") or "gemini-3.5-flash-lite",
                "status": jdoc.get("status", "completed"),
                "current_step": jdoc.get("current_step", "completed"),
                "progress_percent": jdoc.get("progress_percent", 1.0),
                "step_message": jdoc.get("step_message", "Completed"),
                "error": jdoc.get("error"),
                "created_at": jdoc.get("created_at"),
                "completed_at": jdoc.get("completed_at"),
                "updated_at": jdoc.get("completed_at") or jdoc.get("created_at")
            }
            gen_col.replace_one({"job_id": gen_doc["job_id"]}, gen_doc, upsert=True)
            job_count += 1
        print(f"Total jobs synchronized to 'lesson_generations': {job_count}")

if __name__ == "__main__":
    run_migration()

