# Tests for generation pipeline
from alma_lessons.domain import LessonSpec
from alma_lessons.llm import FakeLLMClient
from alma_lessons.generation import LessonGenerationPipeline

def test_generation_pipeline_two_pass_with_fake_llm():
    fake_llm = FakeLLMClient()
    pipeline = LessonGenerationPipeline(llm_client=fake_llm)

    spec = LessonSpec(
        topic="For Loops",
        programming_language="Python",
        grade_level="Grade 8",
        learning_objectives=["Understand loop concept", "Use range with for loops"],
        desired_depth="standard"
    )

    progress_events = []
    def on_progress(msg, pct):
        progress_events.append((msg, pct))

    lesson, outline = pipeline.run(spec, progress_callback=on_progress)

    assert outline is not None
    assert len(outline.sections) >= 1
    assert lesson is not None
    assert lesson.title == "Mastering For Loops in Python"
    assert len(lesson.sections) >= 1
    assert len(lesson.introduction) >= 1
    assert len(lesson.conclusion) >= 1
    assert len(progress_events) >= 3

    # Check adaptive generation features
    sec1 = lesson.sections[0]
    assert sec1.diagnostic_check is not None
    assert sec1.diagnostic_check.correct_answer != ""
    assert sec1.diagnostic_check.concept_tag is not None
    assert len(sec1.remediation_blocks) >= 1
    assert len(sec1.extension_blocks) >= 1
