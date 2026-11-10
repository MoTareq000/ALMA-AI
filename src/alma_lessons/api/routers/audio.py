import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse

from ...config import config
from ...storage import memory_store
from ...tts import audio_cache, get_tts_client
from ..security import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Audio & Voice"])


@router.get("/audio/{filename}")
def stream_audio(filename: str):
    """Stream a cached MP3 audio file."""
    # Prevent directory traversal
    clean_name = Path(filename).name
    if not clean_name.endswith(".mp3"):
        raise HTTPException(status_code=400, detail="Invalid audio file format")

    file_path = config.audio_cache_dir / clean_name
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(
        path=file_path,
        media_type="audio/mpeg",
        filename=clean_name,
    )


@router.post("/lessons/{lesson_id}/synthesize-audio", dependencies=[Depends(verify_api_key)])
def synthesize_lesson_audio(
    lesson_id: str,
    provider: Optional[str] = None,
    voice_name: Optional[str] = None,
):
    """Synthesize voice narration for all segments of an approved lesson using Google Cloud TTS."""
    session = memory_store.lessons.get(lesson_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Lesson '{lesson_id}' not found")

    version = session.current_version
    if not version or not version.segmentation or not version.segmentation.topics:
        raise HTTPException(status_code=400, detail="Lesson has no segmented topics to synthesize")

    tts_client = get_tts_client(provider=provider)
    chosen_voice = voice_name or config.tts_voice_name
    synthesized_count = 0
    cached_count = 0

    for topic_seg in version.segmentation.topics:
        for seg in topic_seg.segments:
            text = seg.narration_text.strip()
            if not text:
                continue

            cache_key = audio_cache.compute_cache_key(
                text=text,
                voice_name=chosen_voice,
                speaking_rate=config.tts_speaking_rate,
            )
            audio_filename = f"{cache_key}.mp3"

            if audio_cache.has_audio(cache_key):
                cached_count += 1
            else:
                try:
                    audio_bytes = tts_client.synthesize(text=text, voice_name=chosen_voice)
                    audio_cache.save_audio(cache_key, audio_bytes)
                    synthesized_count += 1
                except Exception as err:
                    logger.error("Failed to synthesize segment audio: %s", err)
                    raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {err}")

            seg.audio_file = audio_filename
            seg.audio_url = f"/api/v1/audio/{audio_filename}"

    # Persist updated session
    if hasattr(memory_store, "_persist"):
        memory_store._persist(session)

    return {
        "status": "success",
        "lesson_id": lesson_id,
        "voice": chosen_voice,
        "total_segments": sum(len(t.segments) for t in version.segmentation.topics),
        "synthesized_count": synthesized_count,
        "cached_count": cached_count,
    }

