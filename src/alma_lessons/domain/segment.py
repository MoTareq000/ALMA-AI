from typing import List, Optional
from pydantic import BaseModel, Field
from .assessment import SegmentAssessment

class Segment(BaseModel):
    """An atomic narration unit (typically 45-60 seconds of spoken prose)."""
    topic_title: str
    order_in_topic: int
    order_in_lesson: int
    title: str
    narration_text: str
    word_count: int
    est_seconds: float
    attached_code: Optional[str] = None
    attached_code_language: Optional[str] = None
    assessment: Optional[SegmentAssessment] = None
    audio_file: Optional[str] = Field(default=None, description="Filename of cached MP3 audio file")
    audio_url: Optional[str] = Field(default=None, description="Endpoint or CDN URL to stream the audio file")

    # Template slots architecture: guarantees zero hallucination & pre-rendered audio cacheability
    is_verbatim_cacheable: bool = Field(
        default=True,
        description="Guarantees core narration_text is never rewritten by runtime LLM, allowing its TTS audio to be cached permanently."
    )
    prefix_slot_template: Optional[str] = Field(
        default="{greeting_or_praise}",
        description="Slot for short personalized opening sentence (e.g. 'Welcome back {name}!'). Generated dynamically at runtime."
    )
    suffix_slot_template: Optional[str] = Field(
        default=None,
        description="Slot for short closing wrapper sentence referencing student's progress before the micro-check."
    )


class TopicSegmentation(BaseModel):
    """A topic containing an ordered sequence of narration segments."""
    topic_title: str
    order: int
    purpose: str
    segments: List[Segment] = Field(default_factory=list)

class LessonSegmentation(BaseModel):
    """Complete segmentation of an approved lesson ready for TTS narration."""
    lesson_title: str
    total_segments: int
    est_total_duration_minutes: float
    topics: List[TopicSegmentation] = Field(default_factory=list)
