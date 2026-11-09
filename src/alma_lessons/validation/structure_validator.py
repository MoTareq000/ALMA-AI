import re
from typing import Dict, Any, List
from ..domain import LessonContent, LessonSpec

PLACEHOLDER_REGEX = re.compile(
    r"\b(TODO|TBD|FIXME|LOREM IPSUM|\[INSERT.*?\]|\[PLACEHOLDER.*?\])\b",
    re.IGNORECASE
)

class StructureValidator:
    """Validates structural requirements, objective coverage, and placeholder absence."""

    def validate(self, lesson: LessonContent, spec: LessonSpec) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        # 1. Title check
        if not lesson.title or len(lesson.title.strip()) < 3:
            errors.append("Lesson title is missing or too short.")

        # 2. Introduction & Conclusion presence
        if not lesson.introduction:
            errors.append("Lesson is missing an Introduction section.")
        if not lesson.conclusion:
            errors.append("Lesson is missing a Conclusion section.")

        # 3. Sections presence
        if not lesson.sections:
            errors.append("Lesson must contain at least one instructional section.")
        else:
            for s in lesson.sections:
                if not s.blocks:
                    errors.append(f"Section '{s.title}' contains zero content blocks.")

        # 4. Objective coverage map
        covered_objectives = set()
        for s in lesson.sections:
            for obj in s.covers_objectives:
                covered_objectives.add(obj.strip().lower())

        uncovered = []
        for target_obj in spec.learning_objectives:
            target_norm = target_obj.strip().lower()
            # Check for direct match or substring match
            found = any(target_norm in cov or cov in target_norm for cov in covered_objectives)
            if not found:
                uncovered.append(target_obj)

        if uncovered:
            warnings.append(
                f"Some learning objectives may not be explicitly mapped to sections: {', '.join(uncovered)}"
            )

        # 5. Placeholder detection & code block validation
        all_blocks = lesson.introduction + [b for s in lesson.sections for b in s.blocks] + lesson.conclusion
        for i, b in enumerate(all_blocks):
            # Check text fields
            text_to_check = b.text or ""
            if b.items:
                text_to_check += " " + " ".join(b.items)
            if b.code:
                text_to_check += " " + b.code

            match = PLACEHOLDER_REGEX.search(text_to_check)
            if match:
                warnings.append(f"Potential placeholder '{match.group(0)}' detected in block #{i+1}.")

            if b.type == "code":
                if not b.code or len(b.code.strip()) == 0:
                    errors.append(f"Code block #{i+1} has no code snippet.")
                if not b.language:
                    warnings.append(f"Code block #{i+1} does not specify language.")

        # 6. Duration & Word Budget Check
        target_mins = spec.target_duration_minutes or 15
        expected_words = target_mins * 140
        min_recommended_words = int(expected_words * 0.45)
        max_recommended_words = int(expected_words * 1.30)
        if lesson.total_words() < min_recommended_words:
            warnings.append(
                f"Lesson length ({lesson.total_words()} words) is significantly below the target duration budget "
                f"({target_mins} min target ~ {expected_words} words). Consider generating with a deeper depth."
            )
        elif lesson.total_words() > max_recommended_words:
            warnings.append(
                f"Lesson length ({lesson.total_words()} words) exceeds target duration budget by >30% "
                f"({target_mins} min target ~ {expected_words} words). Consider trimming sections to prevent student fatigue."
            )

        # 7. Adaptive Architecture & Diagnostic Check Validation
        adaptive_count = 0
        for s in lesson.sections:
            if s.diagnostic_check:
                adaptive_count += 1
                if not s.diagnostic_check.correct_answer:
                    errors.append(f"Section '{s.title}' diagnostic check has no correct answer specified.")
                if s.diagnostic_check.options and s.diagnostic_check.correct_answer not in s.diagnostic_check.options:
                    warnings.append(
                        f"Section '{s.title}' diagnostic check correct answer is not present in its options list."
                    )
                if not s.diagnostic_check.concept_tag:
                    warnings.append(
                        f"Section '{s.title}' diagnostic check is missing a canonical 'concept_tag' for student mastery tracking."
                    )
            else:
                warnings.append(f"Section '{s.title}' is missing an in-situ diagnostic check for adaptive routing.")

        # 8. Practice Puzzles & Hands-On Exercises Check
        if not lesson.puzzles and not lesson.exercises:
            warnings.append("Lesson contains no interactive puzzles or hands-on coding exercises.")

        return {
            "check": "Structure & Coverage",
            "passed": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "total_blocks": lesson.total_blocks(),
            "total_adaptive_blocks": lesson.total_adaptive_blocks(),
            "total_words": lesson.total_words(),
            "target_duration_minutes": target_mins,
            "est_duration_minutes": round(lesson.total_words() / 140.0, 1),
            "adaptive_sections_count": adaptive_count,
        }
