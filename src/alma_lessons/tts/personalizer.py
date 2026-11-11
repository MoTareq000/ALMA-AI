"""
Adaptive Narration Personalizer
================================
Injects dynamic, personalized pedagogical wrappers into slide narration:
- Student's first name
- Current learning streak
- Diagnosed past misconceptions / struggling concepts
- Interactive checkpoint setups & final congratulatory praise
"""

from typing import Tuple, List
from ..storage.student_repository import StudentProfile
from ..domain.segment import Segment


def build_personalized_script(
    student: StudentProfile,
    segment: Segment,
    slide_idx: int,
    total_slides: int,
    lesson_title: str = "",
) -> Tuple[str, str, str, str]:
    """Generates (prefix, core_text, suffix, full_script) for a given student and slide.

    Guarantees:
    - Core concept text is 100% preserved.
    - Student's first name, streak, and learning context are naturally spoken.
    """
    name = student.first_name.strip()
    streak = student.current_streak
    struggles: List[str] = [
        s.concept_label for s in student.struggling_concepts if s.times_wrong >= 2
    ]

    is_first = (slide_idx == 0)
    is_last = (slide_idx == total_slides - 1)
    has_code = bool(segment.attached_code and segment.attached_code.strip())
    has_assessment = bool(segment.assessment)

    # 1. Prefix: Opening personalized greeting or coaching prompt
    if is_first:
        prefix_parts = [f"Hey {name}!"]
        if streak >= 3:
            prefix_parts.append(f"Awesome to see your {streak}-lesson streak going strong.")
        else:
            prefix_parts.append("Ready to learn something new today?")

        if struggles:
            prefix_parts.append(
                f"We'll connect this to {struggles[0]} so everything makes total sense."
            )
        elif lesson_title:
            prefix_parts.append(f"Today we're mastering {lesson_title}.")
        prefix = " ".join(prefix_parts)

    elif is_last:
        prefix = f"Outstanding focus, {name}! You've reached the final concept of this lesson."

    elif has_code:
        # Code coaching callouts
        code_callouts = [
            f"Take a close look at this code snippet, {name}.",
            f"Notice how this example works, {name}.",
            f"Check out the structure in this example, {name}.",
        ]
        prefix = code_callouts[slide_idx % len(code_callouts)]

    else:
        # Conceptual progression callouts
        interleaved_mentions = [
            f"Here is a key concept to keep in mind, {name}:",
            f"Notice how this ties together, {name}:",
            f"Let's break down this next idea, {name}:",
            f"Pay special attention here, {name}:",
        ]
        prefix = interleaved_mentions[slide_idx % len(interleaved_mentions)]

    # 2. Core Text: The vetted pedagogical explanation
    core_text = segment.narration_text.strip()

    # 3. Suffix: Transition or checkpoint prompt
    if is_first:
        suffix = f"Let's explore the first rule, {name}."
    elif is_last:
        new_streak = streak + 1
        suffix = f"Congratulations on finishing this lesson, {name}! Your learning streak is now {new_streak} lessons strong!"
    elif has_assessment:
        suffix = f"Now it's your turn, {name}! Give the checkpoint below your best shot."
    else:
        transitions = [
            f"Keep this pattern in mind as we move forward, {name}.",
            f"Let's see how this connects to our next step, {name}.",
            f"Great job staying focused, {name}.",
        ]
        suffix = transitions[slide_idx % len(transitions)]

    # 4. Combined Full Script for unified, seamless voice synthesis
    full_script = f"{prefix} {core_text} {suffix}".strip()

    return prefix, core_text, suffix, full_script
