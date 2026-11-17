from typing import Dict, Any, Optional
from ..storage.student_repository import StudentProfile

ARCHETYPES_INFO: Dict[str, Dict[str, Any]] = {
    "foundational": {
        "id": "foundational",
        "name": "Foundational Learner",
        "badge": "🌱 Foundational (High Support)",
        "color": "#10B981",  # Green
        "description": "Benefits from step-by-step breakdown, relatable analogies, patient pacing, and scaffolded warmup exercises.",
        "pacing": "patient",
        "tone": "encouraging",
        "recommended_starting_difficulty": "easy",
        "focus": "Gentle reinforcement & misconception clearing",
    },
    "fast_learner": {
        "id": "fast_learner",
        "name": "Fast Learner",
        "badge": "⚡ Fast Learner (Accelerated)",
        "color": "#3B82F6",  # Blue
        "description": "Grasps core syntax rapidly. Skips basic repetition and thrives on ambitious algorithmic challenges.",
        "pacing": "fast",
        "tone": "direct",
        "recommended_starting_difficulty": "medium",
        "focus": "Direct technical efficiency & extension challenges",
    },
    "practical_code_first": {
        "id": "practical_code_first",
        "name": "Practical Builder",
        "badge": "🛠️ Practical Builder (Code-First)",
        "color": "#F59E0B",  # Amber
        "description": "Learns best by typing and running code immediately. Prefers live demos and hands-on coding over theory.",
        "pacing": "standard",
        "tone": "hands_on",
        "recommended_starting_difficulty": "medium",
        "focus": "Interactive coding challenges & practical implementation",
    },
    "conceptual": {
        "id": "conceptual",
        "name": "Conceptual Thinker",
        "badge": "🧠 Conceptual Thinker (Deep Diver)",
        "color": "#8B5CF6",  # Purple
        "description": "Wants to understand 'how it works under the hood', memory models, execution tracing, and logical flow.",
        "pacing": "thoughtful",
        "tone": "inquisitive",
        "recommended_starting_difficulty": "medium",
        "focus": "Code tracing, logic puzzles & mental models",
    },
}


class ArchetypeClassifier:
    """Classifies student learning archetypes dynamically using learning metrics and preferences."""

    @staticmethod
    def classify(student: StudentProfile, override_archetype: Optional[str] = None) -> str:
        """Determine student archetype based on mastery metrics, error patterns, and preferences."""
        if override_archetype and override_archetype in ARCHETYPES_INFO:
            return override_archetype

        # 1. Check explicit preference or saved archetype
        if student.archetype and student.archetype in ARCHETYPES_INFO and student.archetype != "foundational":
            return student.archetype

        # 2. Analyze mastery metrics
        total_tested = sum(c.times_tested for c in student.struggling_concepts)
        total_correct = sum(c.times_correct for c in student.struggling_concepts)
        total_wrong = sum(c.times_wrong for c in student.struggling_concepts)

        accuracy_rate = (total_correct / max(total_tested, 1)) if total_tested > 0 else 0.5
        struggles_count = len(student.struggling_concepts)
        streak = student.current_streak

        # High struggle, errors, or low accuracy -> Foundational
        if struggles_count >= 2 or total_wrong >= 3 or (total_tested >= 3 and accuracy_rate < 0.60):
            return "foundational"

        # Strong streak and high accuracy -> Fast Learner
        if streak >= 3 and accuracy_rate >= 0.80 and struggles_count <= 1:
            return "fast_learner"

        # Student preferences heuristic
        pref_tone = student.preferences.tone.lower()
        pref_pacing = student.preferences.pacing.lower()

        if pref_tone in ("direct", "gamified") or pref_pacing == "fast":
            return "practical_code_first"

        if pref_tone == "encouraging" and struggles_count > 0:
            return "foundational"

        # Default balanced archetype
        return "conceptual"

    @staticmethod
    def get_info(archetype: str) -> Dict[str, Any]:
        return ARCHETYPES_INFO.get(archetype, ARCHETYPES_INFO["foundational"])
