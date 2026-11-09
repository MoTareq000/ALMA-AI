from typing import Dict, Any, List
from ..domain import LessonContent

class SchemaValidator:
    """Validates that lesson data satisfies the domain Pydantic schema."""

    def validate(self, lesson: LessonContent) -> Dict[str, Any]:
        errors: List[str] = []
        try:
            # Verify serialization and deserialization
            dumped = lesson.model_dump()
            _ = LessonContent.model_validate(dumped)
        except Exception as e:
            errors.append(f"Schema validation error: {str(e)}")

        return {
            "check": "Schema Validity",
            "passed": len(errors) == 0,
            "errors": errors
        }
