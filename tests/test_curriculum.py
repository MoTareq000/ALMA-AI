import io
import pymupdf
from alma_lessons.domain import LessonSpec
from alma_lessons.curriculum import (
    ExtractedCurriculum,
    extract_text_from_pdf,
    extract_curriculum_from_pdf,
)

class MockLLMResponse:
    def __init__(self, data):
        self.parsed_json = data

class MockLLMClient:
    def __init__(self, return_data):
        self.return_data = return_data

    def generate(self, *args, **kwargs):
        return MockLLMResponse(self.return_data)


def create_sample_pdf(title: str, text: str) -> bytes:
    """Helper to create an in-memory single-page PDF with pymupdf."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), f"{title}\n\n{text}")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_extract_text_from_pdf():
    pdf_bytes = create_sample_pdf(
        "Cambridge IGCSE Computer Science 0478",
        "Topic 2.2: Iteration and Count-Controlled Loops in Python.\nLearning Objective: Candidates should be able to use for loops with range()."
    )
    extracted_text, pages = extract_text_from_pdf(pdf_bytes)
    assert pages == 1
    assert "Cambridge IGCSE" in extracted_text
    assert "Count-Controlled Loops" in extracted_text


def test_extract_curriculum_from_pdf():
    pdf_bytes = create_sample_pdf(
        "Syllabus Document",
        "Standards: CSTA 2-AP-10. Grade 8 Python Loops."
    )

    mock_data = {
        "topic": "For Loops and Iteration",
        "programming_language": "Python",
        "grade_level": "Grade 8",
        "learning_objectives": [
            "Explain why loops avoid repetitive code",
            "Use range(stop) and range(start, stop)",
            "Accumulate values inside a loop body"
        ],
        "curriculum_references": ["CSTA 2-AP-10", "CSTA 2-AP-12"],
        "prerequisites": ["Variables", "Print statements"],
        "curriculum_scope_notes": "Limit to single count-controlled loops; do not introduce while loops or nested loops yet."
    }

    mock_client = MockLLMClient(return_data=mock_data)
    extracted = extract_curriculum_from_pdf(pdf_bytes, mock_client)

    assert isinstance(extracted, ExtractedCurriculum)
    assert extracted.topic == "For Loops and Iteration"
    assert extracted.grade_level == "Grade 8"
    assert len(extracted.learning_objectives) == 3
    assert "CSTA 2-AP-10" in extracted.curriculum_references
    assert "Limit to single" in extracted.curriculum_scope_notes
    assert extracted.source_pages_count == 1


def test_lesson_spec_with_scope_notes():
    spec = LessonSpec(
        topic="For Loops",
        programming_language="Python",
        grade_level="Grade 8",
        learning_objectives=["Understand loops"],
        curriculum_references=["CSTA 2-AP-10"],
        curriculum_scope_notes="No nested loops"
    )
    assert spec.curriculum_scope_notes == "No nested loops"
    assert "CSTA 2-AP-10" in spec.curriculum_references
