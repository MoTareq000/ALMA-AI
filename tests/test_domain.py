# Tests for domain models
from alma_lessons.domain import (
    LessonSpec,
    LessonContent,
    Block,
    Section,
    LessonState,
    validate_transition,
)

def test_lesson_spec_creation():
    spec = LessonSpec(
        topic="While Loops",
        programming_language="Python",
        grade_level="Grade 9",
        learning_objectives=["Understand while loop condition", "Avoid infinite loops"],
        desired_depth="standard"
    )
    assert spec.topic == "While Loops"
    assert spec.programming_language == "Python"
    assert len(spec.learning_objectives) == 2

def test_lesson_content_word_and_block_count():
    lesson = LessonContent(
        title="Intro to Python",
        programming_language="Python",
        grade_level="Grade 7",
        introduction=[Block(type="paragraph", text="Welcome to the programming world where code shapes technology.")],
        objectives=["Learn syntax"],
        sections=[
            Section(
                order=1,
                title="Variables",
                purpose="Store data",
                covers_objectives=["Learn syntax"],
                blocks=[
                    Block(type="paragraph", text="A variable is like a labeled container storing a piece of information."),
                    Block(type="code", language="Python", code="score = 10\nprint(score)", expected_output="10"),
                    Block(type="callout", callout_type="tip", text="Choose descriptive variable names.")
                ]
            )
        ],
        conclusion=[Block(type="paragraph", text="Now you know how variables work.")]
    )
    assert lesson.total_blocks() == 5
    # Non-code prose words should be counted correctly
    assert lesson.total_words() > 0

def test_state_transitions():
    assert validate_transition(LessonState.DRAFT, LessonState.VALIDATING) is True
    assert validate_transition(LessonState.VALIDATING, LessonState.AWAITING_REVIEW) is True
    assert validate_transition(LessonState.AWAITING_REVIEW, LessonState.APPROVED) is True
    assert validate_transition(LessonState.AWAITING_REVIEW, LessonState.REJECTED) is True
    assert validate_transition(LessonState.REJECTED, LessonState.APPROVED) is False

def test_assessment_models():
    from alma_lessons.domain import SegmentAssessment, PuzzleChallenge, CodingExercise

    assessment = SegmentAssessment(
        question_type="mcq",
        spoken_tts_prompt="Quick check! Which loop repeats until a condition is false?",
        question_text="Which loop statement repeats until a condition is false?",
        options=["while", "for", "repeat", "goto"],
        correct_answer="while",
        explanation="A while loop tests its condition before every iteration."
    )
    assert assessment.question_type == "mcq"
    assert "while" in assessment.options

    puzzle = PuzzleChallenge(
        puzzle_type="predict_output",
        title="Trace the Counter",
        description="Predict final count",
        code_snippet="c = 0\nwhile c < 3: c += 1",
        correct_order_or_answer="3",
        explanation="Loops 3 times"
    )
    assert puzzle.puzzle_type == "predict_output"

    exercise = CodingExercise(
        title="Loop Practice",
        difficulty="easy",
        task_description="Write a countdown loop",
        starter_code="n = 5\n# loop here",
        hints=["Use while n > 0"],
        solution_code="n = 5\nwhile n > 0: print(n); n -= 1",
        expected_output="5 4 3 2 1"
    )
    assert exercise.difficulty == "easy"

def test_adaptive_section_and_diagnostic():
    from alma_lessons.domain import DiagnosticQuestion, Section, Block

    diag = DiagnosticQuestion(
        concept_tag="zero_indexing",
        question_text="What is the first index in range(5)?",
        options=["0", "1", "5", "None"],
        correct_answer="0",
        misconception_map={"1": "Thought 1-based indexing"},
        explanation="Python range starts at 0 by default."
    )
    assert diag.concept_tag == "zero_indexing"
    sec = Section(
        order=1,
        title="Loop Basics",
        purpose="Teach zero indexing",
        blocks=[Block(type="paragraph", text="Loops start at 0 by default in range.")],
        diagnostic_check=diag,
        remediation_blocks=[Block(type="paragraph", text="Remember: computers count from 0.")],
        extension_blocks=[Block(type="paragraph", text="Advanced: you can specify custom starts like range(2, 5).")]
    )
    assert sec.diagnostic_check.correct_answer == "0"
    assert len(sec.remediation_blocks) == 1
    assert len(sec.extension_blocks) == 1
    assert sec.core_words() > 0
    assert sec.remediation_words() > 0
    assert sec.extension_words() > 0

