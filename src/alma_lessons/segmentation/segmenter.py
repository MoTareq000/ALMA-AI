import re
from typing import List, Optional
from ..domain import LessonContent, LessonSegmentation, TopicSegmentation, Segment, Block
from ..config import config

class BasicLessonSegmenter:
    """Basic segmentation engine splitting approved lessons into topics and 45-60s narration units."""

    def __init__(self, words_per_minute: int = None):
        self.wpm = words_per_minute or config.default_words_per_minute
        # Target ~105-140 words per segment (~45-60s at 140 wpm)
        self.target_words_min = 70
        self.target_words_max = 140

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split prose text into clean sentences."""
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in sentences if s.strip()]

    def _segment_blocks(
        self,
        topic_title: str,
        blocks: List[Block],
        topic_order: int,
        lesson_order_start: int,
    ) -> List[Segment]:
        """Group blocks and sentences into ~45-60s narration segments without splitting code."""
        segments: List[Segment] = []
        current_prose_units: List[str] = []
        current_code: Optional[str] = None
        current_code_lang: Optional[str] = None

        def current_word_count() -> int:
            return sum(len(u.split()) for u in current_prose_units)

        def flush_segment(title_suffix: str = ""):
            nonlocal current_prose_units, current_code, current_code_lang
            if not current_prose_units and not current_code:
                return

            narration = " ".join(current_prose_units).strip()
            if not narration and current_code:
                narration = f"Here is the code demonstration for {topic_title}."

            words = len(narration.split())
            est_secs = round((words / max(self.wpm, 1)) * 60.0, 1)
            # Minimum duration floor for code demonstration segments
            if current_code and est_secs < 20.0:
                est_secs = 25.0

            seg_order_in_topic = len(segments) + 1
            seg_order_in_lesson = lesson_order_start + len(segments)
            seg_title = f"{topic_title} - Part {seg_order_in_topic}" if title_suffix == "" else f"{topic_title} ({title_suffix})"

            segments.append(Segment(
                topic_title=topic_title,
                order_in_topic=seg_order_in_topic,
                order_in_lesson=seg_order_in_lesson,
                title=seg_title,
                narration_text=narration,
                word_count=words,
                est_seconds=est_secs,
                attached_code=current_code,
                attached_code_language=current_code_lang,
                is_verbatim_cacheable=True,
                prefix_slot_template="{greeting_intro}" if seg_order_in_lesson == 1 else "{praise_or_transition}",
                suffix_slot_template=None,
            ))

            current_prose_units = []
            current_code = None
            current_code_lang = None

        for b in blocks:
            if b.type == "code":
                # Code block stays attached to the preceding prose; flush segment
                current_code = b.code
                current_code_lang = b.language
                flush_segment()
            elif b.type == "paragraph" and b.text:
                sentences = self._split_into_sentences(b.text)
                for sentence in sentences:
                    sentence_words = len(sentence.split())
                    if current_word_count() + sentence_words > self.target_words_max and current_word_count() >= self.target_words_min:
                        flush_segment()
                    current_prose_units.append(sentence)
            elif b.type == "callout" and b.text:
                callout_text = f"Tip: {b.text}" if b.callout_type == "tip" else f"Note: {b.text}"
                current_prose_units.append(callout_text)
                if current_word_count() >= self.target_words_max:
                    flush_segment()
            elif b.type == "list" and b.items:
                for itm in b.items:
                    current_prose_units.append(f"Key point: {itm}")
                if current_word_count() >= self.target_words_max:
                    flush_segment()

        # Flush any remaining text/code
        flush_segment()

        return segments

    def segment_lesson(
        self,
        lesson: LessonContent,
        spec=None,
        assessment_generator=None,
        topic_assessment_generator=None,
    ) -> LessonSegmentation:
        """Partition entire lesson into topic buckets and atomic narration segments."""
        topics: List[TopicSegmentation] = []
        global_order = 1

        # 1. Introduction Topic
        if lesson.introduction:
            intro_segs = self._segment_blocks("Introduction", lesson.introduction, topic_order=1, lesson_order_start=global_order)
            topics.append(TopicSegmentation(
                topic_title="Introduction",
                order=1,
                purpose="Engaging lesson overview and context setting",
                segments=intro_segs
            ))
            global_order += len(intro_segs)

        # 2. Main Instruction Sections
        for sec in lesson.sections:
            sec_order = len(topics) + 1
            sec_segs = self._segment_blocks(sec.title, sec.blocks, topic_order=sec_order, lesson_order_start=global_order)
            topics.append(TopicSegmentation(
                topic_title=sec.title,
                order=sec_order,
                purpose=sec.purpose,
                segments=sec_segs
            ))
            global_order += len(sec_segs)

        # 3. Conclusion Topic
        if lesson.conclusion:
            concl_order = len(topics) + 1
            concl_segs = self._segment_blocks("Conclusion & Next Steps", lesson.conclusion, topic_order=concl_order, lesson_order_start=global_order)
            topics.append(TopicSegmentation(
                topic_title="Conclusion & Next Steps",
                order=concl_order,
                purpose="Summary, celebration of milestones, and practical challenges",
                segments=concl_segs
            ))
            global_order += len(concl_segs)

        # Attach micro-check assessment questions (batched per topic preferred)
        if topic_assessment_generator and spec:
            for t in topics:
                try:
                    topic_checks = topic_assessment_generator(spec, t.topic_title, t.purpose, t.segments)
                    for seg in t.segments:
                        if seg.order_in_topic in topic_checks:
                            seg.assessment = topic_checks[seg.order_in_topic]
                except Exception:
                    pass
        elif assessment_generator and spec:
            for t in topics:
                for seg in t.segments:
                    try:
                        seg.assessment = assessment_generator(spec, seg, parent_topic_purpose=t.purpose)
                    except TypeError:
                        seg.assessment = assessment_generator(spec, seg)
                    except Exception:
                        pass

        # Configure suffix slot templates based on assessment presence
        for t in topics:
            for seg in t.segments:
                if seg.assessment:
                    seg.suffix_slot_template = "{micro_check_lead_in}"
                else:
                    seg.suffix_slot_template = "{topic_transition_lead_in}"

        total_segments = sum(len(t.segments) for t in topics)
        total_seconds = sum(s.est_seconds for t in topics for s in t.segments)
        total_minutes = round(total_seconds / 60.0, 1)

        return LessonSegmentation(
            lesson_title=lesson.title,
            total_segments=total_segments,
            est_total_duration_minutes=total_minutes,
            topics=topics
        )

