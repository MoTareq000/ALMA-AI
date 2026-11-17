"""
Adaptive Narration Personalizer
================================
Injects dynamic, personalized pedagogical wrappers into slide narration:
- Student's first name
- Current learning streak
- Diagnosed past misconceptions / struggling concepts
- Interactive checkpoint setups & final congratulatory praise
"""

from typing import Tuple, List, Optional
from ..storage.student_repository import StudentProfile
from ..domain.segment import Segment


def build_personalized_script(
    student: StudentProfile,
    segment: Segment,
    slide_idx: int,
    total_slides: int,
    lesson_title: str = "",
    archetype: Optional[str] = None,
) -> Tuple[str, str, str, str]:
    """Generates (prefix, core_text, suffix, full_script) tailored to the student and archetype.

    Guarantees:
    - Core concept text is 100% preserved.
    - Student's first name, streak, learning context, and archetype pedagogical tone are naturally spoken.
    """
    name = student.first_name.strip()
    streak = student.current_streak
    active_archetype = archetype or getattr(student, "archetype", "foundational") or "foundational"

    struggles: List[str] = [
        s.concept_label for s in student.struggling_concepts if s.times_wrong >= 2
    ]

    is_first = (slide_idx == 0)
    is_last = (slide_idx == total_slides - 1)
    has_code = bool(segment.attached_code and segment.attached_code.strip())
    has_assessment = bool(segment.assessment)

    # 1. Prefix: Opening personalized greeting or coaching prompt
    if is_first:
        if active_archetype == "foundational":
            prefix_parts = [f"Welcome {name}! Let's take this step by step together."]
        elif active_archetype == "fast_learner":
            prefix_parts = [f"Hey {name}! Great momentum — let's power right into this."]
        elif active_archetype == "practical_code_first":
            prefix_parts = [f"Hey {name}! We're jumping straight into the code today."]
        else:  # conceptual
            prefix_parts = [f"Hey {name}! Today we explore the inner workings of this concept."]

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
        if active_archetype == "foundational":
            prefix = f"Proud of your persistence, {name}! You've reached the final concept of this lesson."
        elif active_archetype == "fast_learner":
            prefix = f"Rapid progress, {name}! Final concept before the mastery challenge."
        else:
            prefix = f"Outstanding focus, {name}! You've reached the final concept of this lesson."

    elif has_code:
        # Code coaching callouts adapted to archetype
        if active_archetype == "practical_code_first":
            code_callouts = [
                f"Check out this code demonstration in action, {name}:",
                f"Notice how this snippet executes, {name}:",
                f"Take a hands-on look at the syntax here, {name}:",
            ]
        elif active_archetype == "foundational":
            code_callouts = [
                f"Take your time examining this code, {name}. We will break it down together:",
                f"Notice this gentle example, {name}:",
                f"Let's walk through this snippet line by line, {name}:",
            ]
        elif active_archetype == "conceptual":
            code_callouts = [
                f"Observe how the computer processes this code internally, {name}:",
                f"Trace the variable flow in this snippet, {name}:",
                f"Notice the underlying design pattern here, {name}:",
            ]
        else:  # fast_learner
            code_callouts = [
                f"Scan this snippet, {name}. Notice the efficient pattern:",
                f"Quick glance at the implementation, {name}:",
                f"Spot the key construct in this code, {name}:",
            ]
        prefix = code_callouts[slide_idx % len(code_callouts)]

    else:
        # Conceptual progression callouts adapted to archetype
        if active_archetype == "foundational":
            interleaved_mentions = [
                f"Here is a friendly foundation to keep in mind, {name}:",
                f"No rush at all, {name}. Let's understand this idea:",
                f"Remember, {name}, every expert was once a beginner. Notice:",
            ]
        elif active_archetype == "fast_learner":
            interleaved_mentions = [
                f"Core takeaway here, {name}:",
                f"Key rule to lock in, {name}:",
                f"Here is the essential mechanics, {name}:",
            ]
        else:
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
        if active_archetype == "foundational":
            suffix = f"Give this checkpoint a try, {name}! Take all the time you need."
        elif active_archetype == "fast_learner":
            suffix = f"Test your speed on this checkpoint, {name}!"
        elif active_archetype == "practical_code_first":
            suffix = f"Time for a quick code check below, {name}!"
        else:
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
