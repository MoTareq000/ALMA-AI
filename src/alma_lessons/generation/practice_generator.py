from typing import List
import structlog
from ..domain import (
    PuzzleChallenge,
    CodingExercise,
    PracticeSet,
    PracticeCreateRequest,
)
from ..llm.interface import BaseLLMClient
from .prompts import prompt_manager

logger = structlog.get_logger(__name__)


class CoursePracticeGenerator:
    """Generates standalone course practice challenge sets decoupled from lesson lectures."""

    def __init__(self, llm_client: BaseLLMClient):
        self.client = llm_client

    def generate_practice_set(
        self,
        request: PracticeCreateRequest,
    ) -> PracticeSet:
        """Synthesize interactive logic puzzles and 3-tier adaptive coding challenges for a course topic."""
        concepts_str = ", ".join(request.concepts_to_cover) if request.concepts_to_cover else f"Core syntax, idioms, and applications of {request.topic}"

        prompt = prompt_manager.render("course_practice.md", {
            "TOPIC": request.topic,
            "PROGRAMMING_LANGUAGE": request.programming_language,
            "GRADE_LEVEL": request.grade_level,
            "CONCEPTS_TO_COVER": concepts_str,
        })

        system_prompt = prompt_manager.render("system.md", {
            "grade_level": request.grade_level,
            "programming_language": request.programming_language,
        })

        logger.info(
            "generating_course_practice_set",
            topic=request.topic,
            language=request.programming_language,
        )

        response = self.client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            json_mode=True,
            temperature=0.3,
        )
        data = response.parsed_json or {}

        puzzles: List[PuzzleChallenge] = []
        for p in data.get("puzzles", []):
            try:
                puzzles.append(PuzzleChallenge(**p))
            except Exception as pe:
                logger.warning("invalid_puzzle_schema", error=str(pe))

        exercises: List[CodingExercise] = []
        for e in data.get("exercises", []):
            try:
                exercises.append(CodingExercise(**e))
            except Exception as ee:
                logger.warning("invalid_exercise_schema", error=str(ee))

        practice_set = PracticeSet(
            topic=request.topic,
            course_id=request.course_id,
            module_id=request.module_id,
            programming_language=request.programming_language,
            grade_level=request.grade_level,
            concepts_covered=request.concepts_to_cover or [request.topic],
            puzzles=puzzles,
            exercises=exercises,
        )

        return practice_set
