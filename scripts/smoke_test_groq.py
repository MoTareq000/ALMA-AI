import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "src"))
sys.path.insert(0, str(root))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


from alma_lessons.domain import LessonSpec
from alma_lessons.llm import GroqLLMClient
from alma_lessons.generation import LessonGenerationPipeline
from alma_lessons.validation import ValidationRunner
from alma_lessons.segmentation import BasicLessonSegmenter
from alma_lessons.storage import memory_store

print("Starting Groq Smoke Test...")
generator_client = GroqLLMClient(default_model="openai/gpt-oss-120b")

spec = LessonSpec(
    topic="Conditionals and If-Else Statements",
    programming_language="Python",
    grade_level="Grade 8",
    learning_objectives=[
        "Understand boolean logic and comparisons (==, !=, <, >)",
        "Write if-else statements to make decisions in Python",
        "Handle multiple branches with elif"
    ],
    desired_depth="standard",
    prerequisites=["Variables", "Basic print statements"]
)

pipeline = LessonGenerationPipeline(llm_client=generator_client)
def on_progress(msg, pct):
    print(f"[{int(pct*100)}%] {msg}")

lesson, outline = pipeline.run(spec, progress_callback=on_progress)
print("\nGenerated Lesson Title:", lesson.title)
print("Sections count:", len(lesson.sections))
for s in lesson.sections:
    print(f" - Section {s.order}: {s.title} ({len(s.blocks)} blocks)")

validator = ValidationRunner()
print("\nRunning Validation...")
report = validator.run(lesson, spec)
print("Overall Validation Status:", report["overall_status"])


segmenter = BasicLessonSegmenter()
segmentation = segmenter.segment_lesson(lesson)
print(f"\nSegmentation: {segmentation.total_segments} segments, ~{segmentation.est_total_duration_minutes} mins")

session = memory_store.create_lesson(spec, lesson, validation_report=report)
print(f"Stored in memory session: {session.lesson_id} (Version: v{session.current_version_no}, State: {session.current_version.state})")
print("\nSMOKE TEST COMPLETED SUCCESSFULLY!")
