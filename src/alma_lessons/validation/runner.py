from typing import Dict, Any, List
from ..domain import LessonContent, LessonSpec
from .schema_validator import SchemaValidator
from .structure_validator import StructureValidator

class ValidationRunner:
    """Coordinates deterministic validators (schema, structure, objective coverage, placeholders)."""

    def __init__(self):
        self.schema_validator = SchemaValidator()
        self.structure_validator = StructureValidator()

    def run(self, lesson: LessonContent, spec: LessonSpec) -> Dict[str, Any]:
        schema_res = self.schema_validator.validate(lesson)
        structure_res = self.structure_validator.validate(lesson, spec)

        # Aggregate blocking errors vs warnings
        all_errors: List[str] = []
        all_warnings: List[str] = []

        all_errors.extend(schema_res.get("errors", []))
        all_errors.extend(structure_res.get("errors", []))
        all_warnings.extend(structure_res.get("warnings", []))

        has_blocking = len(all_errors) > 0
        overall_status = "FAILED" if has_blocking else ("WARNINGS" if all_warnings else "PASSED")

        return {
            "overall_status": overall_status,
            "has_blocking_errors": has_blocking,
            "errors": all_errors,
            "warnings": all_warnings,
            "schema_report": schema_res,
            "structure_report": structure_res,
            "word_count": structure_res.get("total_words", 0),
            "block_count": structure_res.get("total_blocks", 0),
        }

