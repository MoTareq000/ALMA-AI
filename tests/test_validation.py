# Tests for validation models
from alma_lessons.domain import LessonSpec, LessonContent, Section, Block
from alma_lessons.validation import SchemaValidator, StructureValidator, ValidationRunner
from alma_lessons.llm import FakeLLMClient

def test_schema_validator_valid():
    validator = SchemaValidator()
    lesson = LessonContent(
        title="Valid Lesson",
        programming_language="JavaScript",
        grade_level="Grade 10",
        introduction=[Block(type="paragraph", text="Hello JavaScript learners!")],
        objectives=["Learn let and const"],
        sections=[
            Section(
                order=1,
                title="Variables in JS",
                purpose="Learn let and const",
                covers_objectives=["Learn let and const"],
                blocks=[Block(type="paragraph", text="In JavaScript, let creates reassignable variables.")]
            )
        ],
        conclusion=[Block(type="paragraph", text="Conclusion text.")]
    )
    report = validator.validate(lesson)
    assert report["passed"] is True
    assert len(report["errors"]) == 0

def test_structure_validator_catches_empty_and_placeholders():
    validator = StructureValidator()
    spec = LessonSpec(
        topic="Functions",
        programming_language="Python",
        learning_objectives=["Define a function", "Return values"]
    )
    # Defective lesson with TODO placeholder and empty code
    bad_lesson = LessonContent(
        title="",  # Empty title
        programming_language="Python",
        grade_level="Grade 8",
        introduction=[],  # Missing introduction
        objectives=["Define a function"],
        sections=[
            Section(
                order=1,
                title="Def syntax",
                purpose="teach def",
                covers_objectives=["Define a function"],
                blocks=[
                    Block(type="paragraph", text="TODO: fill in this paragraph later"),
                    Block(type="code", language="Python", code="")  # Empty code
                ]
            )
        ],
        conclusion=[Block(type="paragraph", text="Done")]
    )
    report = validator.validate(bad_lesson, spec)
    assert report["passed"] is False
    assert any("title" in err.lower() for err in report["errors"])
    assert any("introduction" in err.lower() for err in report["errors"])
    assert any("TODO" in warn for warn in report["warnings"])
    assert any("Return values" in warn for warn in report["warnings"])

def test_validation_runner():
    runner = ValidationRunner()
    spec = LessonSpec(
        topic="For Loops",
        programming_language="Python",
        learning_objectives=["Understand loop concept"]
    )
    lesson = LessonContent(
        title="Mastering For Loops",
        programming_language="Python",
        grade_level="Grade 8",
        introduction=[Block(type="paragraph", text="Introductory text.")],
        objectives=["Understand loop concept"],
        sections=[
            Section(
                order=1,
                title="Loops",
                purpose="teach loops",
                covers_objectives=["Understand loop concept"],
                blocks=[
                    Block(type="paragraph", text="Loops repeat instructions."),
                    Block(type="code", language="Python", code="for i in range(3): print(i)")
                ]
            )
        ],
        conclusion=[Block(type="paragraph", text="Conclusion.")]
    )
    result = runner.run(lesson, spec)
    assert result["overall_status"] in ["PASSED", "WARNINGS"]
    assert result["has_blocking_errors"] is False
    assert result["schema_report"]["passed"] is True
    assert result["structure_report"]["passed"] is True

