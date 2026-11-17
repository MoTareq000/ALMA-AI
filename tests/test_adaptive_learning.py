import pytest
from alma_lessons.domain import (
    LessonSpec,
    LessonContent,
    Section,
    Block,
    CodingExercise,
    DifficultyLadder,
    DIFFICULTY_METADATA,
)
from alma_lessons.classification import ArchetypeClassifier, ARCHETYPES_INFO
from alma_lessons.storage.student_repository import StudentProfile, StudentPreferences, ConceptMasteryItem
from alma_lessons.segmentation import BasicLessonSegmenter
from alma_lessons.tts import build_personalized_script, get_tts_client, ElevenLabsTTSClient
from alma_lessons.domain.segment import Segment


def test_difficulty_ladder_progression():
    """Verify promotion and demotion state transitions in dynamic difficulty."""
    # Promotion
    assert DifficultyLadder.promote("easy") == "medium"
    assert DifficultyLadder.promote("medium") == "hard"
    assert DifficultyLadder.promote("hard") == "hard"

    # Demotion
    assert DifficultyLadder.demote("hard") == "medium"
    assert DifficultyLadder.demote("medium") == "easy"
    assert DifficultyLadder.demote("easy") == "easy"


def test_difficulty_ladder_exercise_filtering():
    """Verify filtering exercises by difficulty level."""
    exercises = [
        CodingExercise(
            title="Warmup",
            difficulty="easy",
            task_description="Easy task",
            starter_code="# starter",
            solution_code="print('easy')",
            expected_output="easy",
        ),
        CodingExercise(
            title="Core",
            difficulty="medium",
            task_description="Medium task",
            starter_code="# starter",
            solution_code="print('medium')",
            expected_output="medium",
        ),
        CodingExercise(
            title="Mastery",
            difficulty="hard",
            task_description="Hard task",
            starter_code="# starter",
            solution_code="print('hard')",
            expected_output="hard",
        ),
    ]

    easy_match = DifficultyLadder.get_exercise_for_level(exercises, "easy")
    assert easy_match.title == "Warmup"

    med_match = DifficultyLadder.get_exercise_for_level(exercises, "medium")
    assert med_match.title == "Core"

    hard_match = DifficultyLadder.get_exercise_for_level(exercises, "hard")
    assert hard_match.title == "Mastery"


def test_archetype_classifier_foundational():
    """Verify student with struggles or errors is classified as foundational."""
    struggling_student = StudentProfile(
        student_id="s_struggle",
        first_name="Layla",
        last_name="Hassan",
        email="layla@alma.edu",
        student_code="STD-LAY-01",
        grade_level="Grade 7",
        struggling_concepts=[
            ConceptMasteryItem(
                concept_id="loops.range",
                concept_label="range() bounds",
                times_tested=4,
                times_correct=1,
                times_wrong=3,
            ),
            ConceptMasteryItem(
                concept_id="loops.nested",
                concept_label="nested loops",
                times_tested=2,
                times_correct=0,
                times_wrong=2,
            ),
        ],
    )
    detected = ArchetypeClassifier.classify(struggling_student)
    assert detected == "foundational"
    info = ArchetypeClassifier.get_info(detected)
    assert "Foundational" in info["name"]


def test_archetype_classifier_fast_learner():
    """Verify student with high streak and accuracy is classified as fast learner."""
    fast_student = StudentProfile(
        student_id="s_fast",
        first_name="Omar",
        last_name="Tarek",
        email="omar@alma.edu",
        student_code="STD-OMR-01",
        grade_level="Grade 9",
        current_streak=5,
        struggling_concepts=[
            ConceptMasteryItem(
                concept_id="loops.for",
                concept_label="basic for loops",
                times_tested=5,
                times_correct=5,
                times_wrong=0,
            ),
        ],
    )
    detected = ArchetypeClassifier.classify(fast_student)
    assert detected == "fast_learner"
    info = ArchetypeClassifier.get_info(detected)
    assert "Fast Learner" in info["name"]


def test_archetype_classifier_practical_and_override():
    """Verify preference-based classification and manual override."""
    builder_student = StudentProfile(
        student_id="s_builder",
        first_name="Kareem",
        last_name="Adel",
        email="kareem@alma.edu",
        student_code="STD-KAR-01",
        grade_level="Grade 8",
        preferences=StudentPreferences(pacing="fast", tone="direct"),
    )
    detected = ArchetypeClassifier.classify(builder_student)
    assert detected == "practical_code_first"

    # Manual override
    override = ArchetypeClassifier.classify(builder_student, override_archetype="conceptual")
    assert override == "conceptual"


def test_personalized_script_archetypes():
    """Verify personalizer injects archetype-adapted pedagogical prefixes and tones."""
    student = StudentProfile(
        student_id="s1",
        first_name="Youssef",
        last_name="Ali",
        email="youssef@alma.edu",
        student_code="STD-YOU-01",
        grade_level="Grade 8",
    )
    seg = Segment(
        topic_title="Loops",
        order_in_topic=1,
        order_in_lesson=1,
        title="Loop Basics",
        narration_text="A for loop repeats a sequence of statements.",
        word_count=8,
        est_seconds=4.0,
    )

    # Foundational tone
    p_pre, _, _, _ = build_personalized_script(student, seg, 0, 3, archetype="foundational")
    assert "Youssef" in p_pre
    assert "step by step" in p_pre.lower()

    # Fast learner tone
    p_pre_fast, _, _, _ = build_personalized_script(student, seg, 0, 3, archetype="fast_learner")
    assert "Youssef" in p_pre_fast
    assert "momentum" in p_pre_fast.lower() or "power" in p_pre_fast.lower()


def test_segmenter_test_mode_max_slides_clamp():
    """Verify BasicLessonSegmenter clamps to exactly 3 slides when test_mode=True."""
    spec = LessonSpec(
        topic="While Loops",
        learning_objectives=["Understand while loop condition"],
        test_mode=True,
        max_slides=3,
    )
    lesson = LessonContent(
        title="While Loops in Python",
        programming_language="Python",
        grade_level="Grade 8",
        target_duration_minutes=3,
        objectives=["Understand while loop condition"],
        sections=[
            Section(
                order=1,
                title="While Loop Condition",
                purpose="Learn condition",
                covers_objectives=["Understand while loop condition"],
                key_concepts=["while", "condition"],
                blocks=[
                    Block(type="paragraph", text="A while loop tests a condition before every iteration."),
                    Block(type="code", language="python", code="while count < 5:\n    count += 1"),
                    Block(type="paragraph", text="Ensure your loop has an increment to prevent infinite loops."),
                    Block(type="paragraph", text="This concludes our exploration of while loop mechanics."),
                    Block(type="paragraph", text="Extra slide that should be clamped out by test mode."),
                ],
            ),
        ],
    )
    segmenter = BasicLessonSegmenter()
    segmentation = segmenter.segment_lesson(lesson, spec=spec)
    assert segmentation.total_segments <= 3


def test_elevenlabs_tts_client_instantiation():
    """Verify ElevenLabsTTSClient is recognized by get_tts_client factory."""
    client = get_tts_client("elevenlabs")
    assert isinstance(client, ElevenLabsTTSClient)
    assert client.base_url == "https://api.elevenlabs.io/v1/text-to-speech"
