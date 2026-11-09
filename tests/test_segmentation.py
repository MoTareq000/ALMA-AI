# Tests for segmentation
from alma_lessons.domain import LessonContent, Section, Block
from alma_lessons.segmentation import BasicLessonSegmenter

def test_basic_lesson_segmenter():
    segmenter = BasicLessonSegmenter(words_per_minute=140)

    lesson = LessonContent(
        title="Intro to Variables",
        programming_language="Python",
        grade_level="Grade 8",
        introduction=[
            Block(type="paragraph", text="Welcome! Today we will learn about computer memory and variables. Variables allow our programs to remember things."),
            Block(type="callout", callout_type="tip", text="Think of variables as storage boxes with labels.")
        ],
        objectives=["Learn variables"],
        sections=[
            Section(
                order=1,
                title="Declaring Variables",
                purpose="Learn assignment operator",
                covers_objectives=["Learn variables"],
                blocks=[
                    Block(type="paragraph", text="In Python, you create a variable by choosing a name and assigning it a value using the equals sign."),
                    Block(type="code", language="Python", code="player_name = 'Alex'\nprint(player_name)"),
                    Block(type="paragraph", text="Here player_name stores the text Alex. Printing it displays the saved name on the screen.")
                ]
            )
        ],
        conclusion=[
            Block(type="paragraph", text="Congratulations on completing this lesson. Now you can store dynamic data in your code!")
        ]
    )

    segmentation = segmenter.segment_lesson(lesson)

    assert segmentation.lesson_title == "Intro to Variables"
    assert segmentation.total_segments >= 3
    assert segmentation.est_total_duration_minutes > 0.0

    # Ensure code demonstration has attached code preserved
    code_segs = [s for t in segmentation.topics for s in t.segments if s.attached_code]
    assert len(code_segs) >= 1
    assert "player_name" in code_segs[0].attached_code

    # Assert template slots and verbatim cacheability
    first_seg = segmentation.topics[0].segments[0]
    assert first_seg.is_verbatim_cacheable is True
    assert first_seg.prefix_slot_template == "{greeting_intro}"
    assert first_seg.suffix_slot_template is not None

def test_topic_assessment_generator():
    segmenter = BasicLessonSegmenter(words_per_minute=140)
    lesson = LessonContent(
        title="Intro",
        programming_language="Python",
        grade_level="Grade 8",
        introduction=[Block(type="paragraph", text="Welcome to the lesson.")],
        objectives=["Learn Python"],
        sections=[
            Section(
                order=1,
                title="Basics",
                purpose="Learn basics",
                blocks=[Block(type="paragraph", text="Variables store values in Python.")]
            )
        ],
        conclusion=[Block(type="paragraph", text="Great job!")]
    )

    from alma_lessons.domain import SegmentAssessment, LessonSpec

    def mock_topic_generator(spec, topic_title, topic_purpose, segments):
        return {
            1: SegmentAssessment(
                question_type="mcq",
                spoken_tts_prompt="What does a variable do?",
                question_text="What does a variable do?",
                options=["Store data", "Turn off computer"],
                correct_answer="Store data",
                explanation="Variables store data."
            )
        }

    spec = LessonSpec(topic="Python", programming_language="Python", grade_level="Grade 8", learning_objectives=["Learn Python"])
    segmentation = segmenter.segment_lesson(lesson, spec=spec, topic_assessment_generator=mock_topic_generator)
    assert segmentation.topics[0].segments[0].assessment is not None
    assert segmentation.topics[0].segments[0].assessment.correct_answer == "Store data"

