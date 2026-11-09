from fastapi import APIRouter
from ...storage import memory_store, student_repository, job_manager

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
def health_check():
    default_student = student_repository.get_default_student()
    return {
        "status": "online",
        "service": "ALMA AI Lesson Generation & Adaptive Runtime API",
        "version": "1.0.0",
        "lessons_in_store": len(memory_store.lessons),
        "default_student": {
            "name": f"{default_student.first_name} {default_student.last_name}",
            "grade": default_student.grade_level,
            "student_id": default_student.student_id,
        },
        "database_adapter": f"MongoDB ({type(memory_store).__name__})" if "Mongo" in type(memory_store).__name__ else "Local In-Memory"
    }
