from fastapi import APIRouter, UploadFile, File, HTTPException
from ...curriculum.extractor import extract_text_from_pdf, extract_curriculum_from_pdf, ExtractedCurriculum
from ...domain import LessonSpec
from ..deps import get_llm_client
from ..schemas import CurriculumExtractResponse

router = APIRouter(prefix="/curriculum", tags=["Curriculum"])

@router.post("/extract", response_model=CurriculumExtractResponse)
async def extract_curriculum(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported for curriculum extraction")

    try:
        content = await file.read()
        client = get_llm_client()
        extracted: ExtractedCurriculum = extract_curriculum_from_pdf(content, llm_client=client)

        suggested_spec = LessonSpec(
            topic=extracted.topic,
            programming_language=extracted.programming_language,
            grade_level=extracted.grade_level,
            learning_objectives=extracted.learning_objectives,
            curriculum_references=extracted.curriculum_references,
            prerequisites=extracted.prerequisites,
            curriculum_scope_notes=extracted.curriculum_scope_notes,
            target_duration_minutes=15
        )

        return CurriculumExtractResponse(
            raw_text_length=len(extracted.raw_excerpt or ""),
            extracted_metadata=extracted.model_dump(),
            suggested_spec=suggested_spec
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process curriculum PDF: {str(e)}")

