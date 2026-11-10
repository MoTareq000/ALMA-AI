"""ALMA Academy AI Lesson Generation Pipeline package."""

__version__ = "0.1.0"

from .curriculum import ExtractedCurriculum, extract_curriculum_from_pdf, extract_text_from_pdf

__all__ = [
    "__version__",
    "ExtractedCurriculum",
    "extract_curriculum_from_pdf",
    "extract_text_from_pdf",
]
