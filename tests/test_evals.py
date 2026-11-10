import json
from pathlib import Path
from alma_lessons.domain import LessonSpec
from alma_lessons.generation.pipeline import LessonGenerationPipeline
from alma_lessons.segmentation.segmenter import BasicLessonSegmenter
from alma_lessons.llm.fake_client import FakeLLMClient
from alma_lessons.llm.interface import BaseLLMClient, LLMResponse

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TruncatedJSONClient(BaseLLMClient):
    """LLM client returning truncated JSON to verify resilience and repair/fallback handling."""

    def generate(self, prompt: str, system_prompt: str = None, json_mode: bool = True, **kwargs) -> LLMResponse:
        # Return truncated/invalid JSON string
        truncated_json_str = '{"title": "Unfinished Python Lesson", "sections": [{"order": 1, "title": "Intro"'
        parsed = None
        if json_mode:
            try:
                import json_repair
                parsed = json_repair.loads(truncated_json_str)
            except Exception:
                parsed = None

        return LLMResponse(
            content=truncated_json_str,
            parsed_json=parsed,
            model_name="truncated-fake-model",
            prompt_tokens=50,
            completion_tokens=25,
            latency_ms=10.0,
        )


def test_invalid_or_truncated_json_handling():
    """Verify pipeline handles truncated/malformed JSON without unhandled crash."""
    spec = LessonSpec(
        subject="Programming",
        topic="Variables in Python",
        programming_language="Python",
        grade_level="Grade 6",
        learning_objectives=["Understand variables", "Assign values"],
        target_duration_minutes=10,
    )
    client = TruncatedJSONClient()
    pipeline = LessonGenerationPipeline(llm_client=client)

    # generate_outline should either repair with json_repair or fall back to default outline
    outline = pipeline.generate_outline(spec, attempts=2)
    assert outline is not None
    assert len(outline.sections) >= 1
    assert "Variables in Python" in outline.title or "Intro" in outline.sections[0].title


def test_arabic_spec_pipeline():
    """Verify Arabic topic and objectives flow cleanly through generation and segmentation."""
    spec_path = PROJECT_ROOT / "evals" / "specs" / "13_arabic_python_for_loops_gr6.json"
    assert spec_path.exists(), f"Spec file missing: {spec_path}"

    with open(spec_path, "r", encoding="utf-8") as f:
        spec_data = json.load(f)

    spec = LessonSpec(**spec_data)
    assert spec.language == "ar"
    assert "بايثون" in spec.topic

    client = FakeLLMClient()
    pipeline = LessonGenerationPipeline(llm_client=client)
    lesson, outline = pipeline.run(spec)

    assert lesson is not None
    assert outline is not None
    assert len(lesson.sections) > 0

    segmenter = BasicLessonSegmenter()
    segmentation = segmenter.segment_lesson(lesson, spec=spec)
    assert segmentation is not None
    assert len(segmentation.topics) > 0
    assert segmentation.total_segments > 0


def test_scope_notes_pipeline():
    """Verify curriculum_scope_notes are properly carried through LessonSpec and pipeline."""
    spec_path = PROJECT_ROOT / "evals" / "specs" / "03_python_while_loops_scope_notes_gr7.json"
    assert spec_path.exists(), f"Spec file missing: {spec_path}"

    with open(spec_path, "r", encoding="utf-8") as f:
        spec_data = json.load(f)

    spec = LessonSpec(**spec_data)
    assert spec.curriculum_scope_notes is not None
    assert "break" in spec.curriculum_scope_notes

    client = FakeLLMClient()
    pipeline = LessonGenerationPipeline(llm_client=client)
    lesson, outline = pipeline.run(spec)

    assert lesson is not None
    assert outline is not None
    # Verify outline was generated
    assert len(outline.sections) > 0
    # Verify call history recorded the prompt containing scope notes
    prompt_found = any(
        "Focus only on counter-controlled while loops" in call["prompt"]
        for call in client.call_history
    )
    assert prompt_found, "curriculum_scope_notes were not rendered into LLM prompts"

