import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from ...curriculum.extractor import extract_curriculum_from_pdf, ExtractedCurriculum
from ...domain import LessonSpec
from ...config import config
from ..deps import get_llm_client
from ..schemas import CurriculumExtractResponse
from ..security import verify_api_key, rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/curriculum",
    tags=["Curriculum"],
    dependencies=[Depends(verify_api_key)]
)

@router.post("/extract", response_model=CurriculumExtractResponse, dependencies=[Depends(rate_limiter)])
async def extract_curriculum(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported for curriculum extraction")

    try:
        content = await file.read()
        max_bytes = config.max_upload_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds maximum upload size of {config.max_upload_mb} MB"
            )

        if not content.startswith(b"%PDF"):
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is not a valid PDF (invalid magic bytes header)"
            )

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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Internal error processing curriculum PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to process curriculum PDF due to an internal server error. Please ensure the document is not corrupted."
        )
