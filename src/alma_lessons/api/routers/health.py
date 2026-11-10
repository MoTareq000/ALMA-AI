from fastapi import APIRouter
from ...config import config
from ...storage import memory_store, student_repository

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
def health_check():
    is_mongo = "Mongo" in type(memory_store).__name__
    default_student = None
    try:
        default_student = student_repository.get_default_student()
    except Exception:
        pass

    student_info = None
    if default_student:
        student_info = {
            "name": f"{default_student.first_name} {default_student.last_name}",
            "grade": default_student.grade_level,
            "student_id": default_student.student_id,
        }

    # Reports online if MongoDB is connected, degraded if running on in-memory storage while REQUIRE_MONGODB=false
    status = "online" if is_mongo else ("degraded" if not config.require_mongodb else "error")

    return {
        "status": status,
        "service": "ALMA AI Lesson Generation & Adaptive Runtime API",
        "version": "1.0.0",
        "storage_adapter": type(memory_store).__name__,
        "database_adapter": f"MongoDB ({type(memory_store).__name__})" if is_mongo else "Local In-Memory",
        "lessons_in_store": len(memory_store.lessons),
        "default_student": student_info,
        "require_mongodb": config.require_mongodb
    }
