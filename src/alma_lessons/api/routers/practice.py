from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status

from ...domain import (
    PracticeSet,
    PracticeCreateRequest,
    PracticeSubmissionRequest,
    DifficultyLadder,
    DIFFICULTY_METADATA,
)
from ...generation.practice_generator import CoursePracticeGenerator
from ..deps import get_llm_client
from ...storage import memory_store

router = APIRouter(prefix="/practice", tags=["Course Practice Arena"])


@router.post(
    "/generate",
    response_model=PracticeSet,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Course Practice Challenge Set",
    description="Generate interactive logic puzzles and 3-tiered coding exercises (Easy/Medium/Hard) decoupled from lessons."
)
def generate_practice(request: PracticeCreateRequest) -> PracticeSet:
    llm_client = get_llm_client(provider=request.provider, model=request.model)
    generator = CoursePracticeGenerator(llm_client=llm_client)

    try:
        practice_set = generator.generate_practice_set(request)
        memory_store.save_practice_set(practice_set)
        return practice_set
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate course practice challenges: {str(e)}"
        )


@router.get(
    "",
    response_model=List[PracticeSet],
    summary="List Practice Sets",
    description="Retrieve all course practice challenge sets, optionally filtered by course_id."
)
def list_practice_sets(course_id: Optional[str] = Query(None, description="Filter by Course ID")) -> List[PracticeSet]:
    return memory_store.list_practice_sets(course_id=course_id)


@router.get(
    "/{practice_id}",
    response_model=PracticeSet,
    summary="Get Practice Set by ID",
    description="Retrieve specific practice challenges including puzzles and tiered coding exercises."
)
def get_practice_set(practice_id: str) -> PracticeSet:
    practice = memory_store.get_practice_set(practice_id)
    if not practice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Practice set '{practice_id}' not found."
        )
    return practice


@router.post(
    "/{practice_id}/submit",
    summary="Evaluate Practice Submission",
    description="Evaluate student code submission against practice exercise and determine adaptive difficulty ladder progression."
)
def submit_practice_solution(practice_id: str, submission: PracticeSubmissionRequest) -> Dict[str, Any]:
    practice = memory_store.get_practice_set(practice_id)
    if not practice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Practice set '{practice_id}' not found."
        )

    current_level = submission.current_difficulty.lower()
    matched_exercise = DifficultyLadder.get_exercise_for_level(practice.exercises, current_level)

    if not matched_exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No exercise found for difficulty level '{current_level}'."
        )

    code = submission.submitted_code.strip()
    starter = matched_exercise.starter_code.strip()

    # Basic heuristic verification
    is_modified = (code != starter and len(code) > 15)
    has_substantive_code = len(code.split("\n")) >= 2

    is_correct = is_modified and has_substantive_code

    if is_correct:
        next_level = DifficultyLadder.promote(current_level)
        message = f"Outstanding work! Flawless solution at {current_level.upper()} level."
        ladder_action = "promoted" if next_level != current_level else "max_mastery"
    else:
        next_level = DifficultyLadder.demote(current_level)
        message = "Solution needs refinement. Guided scaffolding unlocked."
        ladder_action = "demoted" if next_level != current_level else "keep_level"

    return {
        "status": "correct" if is_correct else "needs_work",
        "previous_difficulty": current_level,
        "new_difficulty": next_level,
        "ladder_action": ladder_action,
        "difficulty_metadata": DIFFICULTY_METADATA.get(next_level, DIFFICULTY_METADATA["medium"]),
        "feedback": message,
        "expected_output": matched_exercise.expected_output,
    }
