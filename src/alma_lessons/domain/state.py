from enum import Enum
from typing import Dict, Set

class LessonState(str, Enum):
    """The 6 lifecycle states of a lesson version."""
    DRAFT = "Draft"
    VALIDATING = "Validating"
    AWAITING_REVIEW = "Awaiting review"
    NEEDS_REVISION = "Needs revision"
    APPROVED = "Approved"
    REJECTED = "Rejected"

# Allowed state transitions as defined in Section 5, Stage D of the Plan
VALID_TRANSITIONS: Dict[LessonState, Set[LessonState]] = {
    LessonState.DRAFT: {
        LessonState.VALIDATING
    },
    LessonState.VALIDATING: {
        LessonState.AWAITING_REVIEW,
        LessonState.NEEDS_REVISION,
        LessonState.REJECTED
    },
    LessonState.AWAITING_REVIEW: {
        LessonState.APPROVED,
        LessonState.NEEDS_REVISION,
        LessonState.REJECTED,
        LessonState.VALIDATING  # When teacher edits and re-triggers validation
    },
    LessonState.NEEDS_REVISION: {
        LessonState.VALIDATING, # After teacher edits or regenerates
        LessonState.REJECTED
    },
    LessonState.APPROVED: {
        LessonState.VALIDATING  # Editing an approved lesson creates/moves to validating
    },
    LessonState.REJECTED: set()  # Terminal state
}

def validate_transition(current: LessonState, target: LessonState) -> bool:
    """Return True if transitioning from current to target is allowed."""
    return target in VALID_TRANSITIONS.get(current, set())
