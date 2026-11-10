import io
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field
from ..generation.prompts import prompt_manager

class ExtractedCurriculum(BaseModel):
    """Structured pedagogical metadata extracted from a curriculum reference PDF."""
    topic: str = Field(description="Detected or inferred core topic")
    programming_language: str = Field(default="Python", description="Programming language")
    grade_level: str = Field(default="Grade 8", description="Target grade or age band")
    learning_objectives: List[str] = Field(default_factory=list, description="Extracted learning objectives")
    curriculum_references: List[str] = Field(default_factory=list, description="Standard codes or syllabus unit tags")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisite concepts")
    curriculum_scope_notes: Optional[str] = Field(default=None, description="Scope boundaries or pedagogical constraints")
    source_pages_count: int = 1
    raw_excerpt: Optional[str] = None


def extract_text_from_pdf(pdf_bytes: bytes, max_pages: int = 15, max_chars: int = 25000) -> Tuple[str, int]:
    """Extract clean text from PDF bytes using PyMuPDF (fitz) or pypdf as fallback."""
    if not pdf_bytes:
        return "", 0

    extracted_pages = []
    total_pages = 0

    # 1. Try PyMuPDF - fastest and highest fidelity
    try:
        import pymupdf
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        total_pages = len(doc)
        pages_to_read = min(total_pages, max_pages)
        for i in range(pages_to_read):
            page_text = doc[i].get_text()
            if page_text and page_text.strip():
                extracted_pages.append(f"--- Page {i + 1} ---\n" + page_text.strip())
        doc.close()
    except Exception:
        extracted_pages = []

    # 2. Fallback to pypdf if PyMuPDF wasn't used or yielded empty text
    if not extracted_pages:
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            total_pages = len(reader.pages)
            pages_to_read = min(total_pages, max_pages)
            for i in range(pages_to_read):
                page_text = reader.pages[i].extract_text()
                if page_text and page_text.strip():
                    extracted_pages.append(f"--- Page {i + 1} ---\n" + page_text.strip())
        except Exception:
            pass

    full_text = "\n\n".join(extracted_pages).strip()
    if len(full_text) > max_chars:
        full_text = full_text[:max_chars] + "\n... [Remaining text truncated for token optimization]"

    return full_text, total_pages


def extract_curriculum_from_pdf(pdf_bytes: bytes, llm_client) -> ExtractedCurriculum:
    """Parse an uploaded PDF and use a lightweight LLM call to extract structured objectives and standards."""
    text, total_pages = extract_text_from_pdf(pdf_bytes)
    if not text or len(text.strip()) < 30:
        raise ValueError("Could not extract readable text from the uploaded PDF. Please ensure it is not an empty or password-protected document.")

    prompt = prompt_manager.render("extract_curriculum.md", {
        "document_text": text
    })

    response = llm_client.generate(
        prompt=prompt,
        system_prompt="You are a precise educational curriculum analyzer. Extract clean structured JSON only.",
        json_mode=True,
        temperature=0.1
    )

    data = response.parsed_json or {}
    
    # Clean and guarantee valid list formats
    objectives = data.get("learning_objectives", [])
    if isinstance(objectives, str):
        objectives = [objectives]
    if not objectives:
        objectives = ["Understand core concepts and execution mechanics"]

    standards = data.get("curriculum_references", [])
    if isinstance(standards, str):
        standards = [standards]

    prereqs = data.get("prerequisites", [])
    if isinstance(prereqs, str):
        prereqs = [prereqs]

    return ExtractedCurriculum(
        topic=data.get("topic") or "Programming Fundamentals",
        programming_language=data.get("programming_language") or "Python",
        grade_level=data.get("grade_level") or "Grade 8",
        learning_objectives=objectives,
        curriculum_references=standards,
        prerequisites=prereqs,
        curriculum_scope_notes=data.get("curriculum_scope_notes"),
        source_pages_count=total_pages,
        raw_excerpt=text[:1200]
    )
