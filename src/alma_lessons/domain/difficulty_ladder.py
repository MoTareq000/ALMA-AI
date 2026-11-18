from typing import List, Optional, Dict, Any
from .assessment import CodingExercise

DIFFICULTY_ORDER = ["easy", "medium", "hard"]

DIFFICULTY_METADATA: Dict[str, Dict[str, Any]] = {
    "easy": {
        "level": 1,
        "name": "Foundational Warmup",
        "badge": "🟢 Easy (Warmup)",
        "color": "#10B981",
        "description": "Guided starter code with direct syntax application.",
        "scaffolding": "High (80% Starter Code)",
    },
    "medium": {
        "level": 2,
        "name": "Core Application",
        "badge": "🟡 Medium (Core Challenge)",
        "color": "#F59E0B",
        "description": "Standard scenario requiring function completion and logic building.",
        "scaffolding": "Moderate (50% Starter Code)",
    },
    "hard": {
        "level": 3,
        "name": "Mastery Edge Case",
        "badge": "🔴 Hard (Mastery Extension)",
        "color": "#EF4444",
        "description": "Multi-step algorithmic problem with minimal scaffolding and edge cases.",
        "scaffolding": "Minimal (20% Starter Code)",
    },
}


class DifficultyLadder:
    """Manages real-time difficulty ladder progression for adaptive student practice."""

    @staticmethod
    def promote(current_level: str) -> str:
        """Move student up one rung on flawless performance."""
        lvl = current_level.lower()
        if lvl == "easy":
            return "medium"
        elif lvl in ("medium", "standard"):
            return "hard"
        return "hard"

    @staticmethod
    def demote(current_level: str) -> str:
        """Step student down one rung when struggling to reinforce core foundations."""
        lvl = current_level.lower()
        if lvl == "hard":
            return "medium"
        elif lvl in ("medium", "standard"):
            return "easy"
        return "easy"

    @staticmethod
    def get_exercise_for_level(
        exercises: List[CodingExercise],
        level: str,
    ) -> Optional[CodingExercise]:
        """Find an exercise matching the requested level, or the closest available."""
        if not exercises:
            return None

        lvl = level.lower()
        # Direct match
        matched = [e for e in exercises if e.difficulty.lower() == lvl]
        if matched:
            return matched[0]

        # Fallback to closest
        if lvl == "hard":
            for fallback in ("medium", "easy"):
                m = [e for e in exercises if e.difficulty.lower() == fallback]
                if m:
                    return m[0]
        elif lvl == "easy":
            for fallback in ("medium", "hard"):
                m = [e for e in exercises if e.difficulty.lower() == fallback]
                if m:
                    return m[0]

        return exercises[0]

