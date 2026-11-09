import logging
from .memory_store import (
    MemoryLessonStore,
    LessonSession,
    LessonVersionRecord,
    memory_store as _default_memory_store
)
from .student_repository import (
    StudentProfile,
    ConceptMasteryItem,
    StudentPreferences,
    BaseStudentRepository,
    LocalStudentRepository,
    student_repository as _default_student_repo,
)
from .session_repository import (
    StudentSessionRecord,
    CheckpointLog,
    DialogueLog,
    BaseSessionRepository,
    MongoSessionRepository,
    LocalSessionRepository,
)
from .job_manager import JobManager, JobRecord, job_manager
from .mongo_client import get_mongo_client, get_mongo_db, is_mongo_connected
from .mongo_student_repository import MongoStudentRepository
from .mongo_lesson_store import MongoLessonStore

logger = logging.getLogger(__name__)

# Determine active database adapters
if is_mongo_connected():
    try:
        student_repository = MongoStudentRepository()
        memory_store = MongoLessonStore()
        session_repository = MongoSessionRepository()
        logger.info("Storage initialized with MongoDB adapters.")
    except Exception as e:
        logger.warning(f"Error initializing MongoDB repositories: {e}. Falling back to in-memory.")
        student_repository = _default_student_repo
        memory_store = _default_memory_store
        session_repository = LocalSessionRepository()
else:
    student_repository = _default_student_repo
    memory_store = _default_memory_store
    session_repository = LocalSessionRepository()

__all__ = [
    "MemoryLessonStore",
    "LessonSession",
    "LessonVersionRecord",
    "memory_store",
    "StudentProfile",
    "ConceptMasteryItem",
    "StudentPreferences",
    "BaseStudentRepository",
    "LocalStudentRepository",
    "student_repository",
    "StudentSessionRecord",
    "CheckpointLog",
    "DialogueLog",
    "BaseSessionRepository",
    "session_repository",
    "MongoSessionRepository",
    "LocalSessionRepository",
    "JobManager",
    "JobRecord",
    "job_manager",
    "get_mongo_client",
    "get_mongo_db",
    "is_mongo_connected",
    "MongoStudentRepository",
    "MongoLessonStore",
]
