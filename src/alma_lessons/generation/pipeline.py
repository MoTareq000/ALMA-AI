from typing import List, Tuple, Optional, Callable, Dict, Any
from ..domain import (
    LessonSpec,
    LessonContent,
    Outline,
    OutlineSection,
    Section,
    Block,
    Segment,
    SegmentAssessment,
    PuzzleChallenge,
    CodingExercise,
    DiagnosticQuestion,
)
from ..llm.interface import BaseLLMClient
from ..config import config
from .prompts import prompt_manager

class LessonGenerationPipeline:
    """Orchestrates two-pass lesson generation with running summary bridges."""

    def __init__(self, llm_client: BaseLLMClient):
        self.client = llm_client

    def _get_system_prompt(self, spec: LessonSpec) -> str:
        return prompt_manager.render("system.md", {
            "grade_level": spec.grade_level,
            "programming_language": spec.programming_language,
        })

    def generate_outline(self, spec: LessonSpec, attempts: int = 2) -> Outline:
        """Pass 1: Generate high-level outline ensuring all objectives are mapped and duration budgeted."""
        target_mins = spec.target_duration_minutes or 15
        words_per_min = config.default_words_per_minute or 140
        total_target_words = target_mins * words_per_min

        system_prompt = self._get_system_prompt(spec)
        outline_prompt = prompt_manager.render("outline.md", {
            "subject": spec.subject,
            "topic": spec.topic,
            "programming_language": spec.programming_language,
            "grade_level": spec.grade_level,
            "desired_depth": spec.desired_depth,
            "target_duration_minutes": target_mins,
            "total_target_words": total_target_words,
            "learning_objectives": spec.learning_objectives,
            "prerequisites": ", ".join(spec.prerequisites) if spec.prerequisites else "None",
            "curriculum_references": ", ".join(spec.curriculum_references) if spec.curriculum_references else "Standard curriculum",
            "curriculum_scope_notes": getattr(spec, "curriculum_scope_notes", None) or "Standard grade-level scope",
            "additional_instructions": spec.additional_instructions or "None",
        })

        for attempt in range(attempts):
            response = self.client.generate(
                prompt=outline_prompt,
                system_prompt=system_prompt,
                json_mode=True,
                temperature=0.2,
            )
            data = response.parsed_json or {}
            try:
                outline = Outline(**data)
                # Verify that outline has sections
                if not outline.sections:
                    raise ValueError("Outline returned zero sections")
                if not outline.target_duration_minutes:
                    outline.target_duration_minutes = target_mins
                if not outline.total_target_words:
                    outline.total_target_words = total_target_words
                # Ensure each section has target_words
                per_sec_words = total_target_words // len(outline.sections)
                for sec in outline.sections:
                    if not sec.target_words:
                        sec.target_words = per_sec_words
                return outline
            except Exception:
                if attempt == attempts - 1:
                    # Fallback default outline if model failed schema
                    per_sec_words = total_target_words // 3
                    return Outline(
                        title=f"Comprehensive Guide to {spec.topic} in {spec.programming_language}",
                        target_duration_minutes=target_mins,
                        total_target_words=total_target_words,
                        sections=[
                            OutlineSection(
                                order=1,
                                title=f"Motivation and Mental Model: {spec.topic}",
                                purpose="Build foundational understanding and mental model",
                                covers_objectives=spec.learning_objectives[:1],
                                key_concepts=["fundamentals", "syntax", "why it matters"],
                                needs_code_example=True,
                                target_words=per_sec_words,
                            ),
                            OutlineSection(
                                order=2,
                                title=f"Core Mechanics and Syntax in {spec.programming_language}",
                                purpose="Step-by-step syntax, execution flow, and variable tracing",
                                covers_objectives=spec.learning_objectives,
                                key_concepts=["implementation", "control flow"],
                                needs_code_example=True,
                                target_words=per_sec_words,
                            ),
                            OutlineSection(
                                order=3,
                                title="Practical Applications, Edge Cases, and Common Pitfalls",
                                purpose="Deep dive with hands-on coding demonstrations and debugging",
                                covers_objectives=spec.learning_objectives,
                                key_concepts=["patterns", "debugging", "best practices"],
                                needs_code_example=True,
                                target_words=per_sec_words,
                            )
                        ]
                    )

    def generate_running_bridge(
        self,
        spec: LessonSpec,
        prev_summary: str,
        section_title: str,
        key_concepts: List[str],
        section_snippet: str,
        next_title: str
    ) -> Dict[str, Any]:
        """Generate a short narrative bridge connecting consecutive sections."""
        prompt = prompt_manager.render("bridge.md", {
            "topic": spec.topic,
            "programming_language": spec.programming_language,
            "previous_summary": prev_summary or "Beginning of lesson",
            "section_title": section_title,
            "key_concepts": ", ".join(key_concepts),
            "section_text_snippet": section_snippet[:400],
            "next_section_title": next_title,
        })
        try:
            resp = self.client.generate(prompt=prompt, json_mode=True, temperature=0.3)
            return resp.parsed_json or {}
        except Exception:
            return {
                "narrative_bridge": f"Having covered {section_title}, we now move directly into {next_title}.",
                "mastered_concepts": key_concepts
            }

    def generate_section(
        self,
        spec: LessonSpec,
        outline: Outline,
        outline_sec: OutlineSection,
        running_summary: str,
        teacher_feedback: Optional[str] = None
    ) -> Section:
        """Generate content blocks for a single section with adaptive learning branches."""
        system_prompt = self._get_system_prompt(spec)
        full_outline_text = "\n".join(f"{s.order}. {s.title} ({s.purpose})" for s in outline.sections)

        target_mins = spec.target_duration_minutes or 15
        total_target_words = target_mins * (config.default_words_per_minute or 140)
        per_sec_target = outline_sec.target_words or (total_target_words // max(len(outline.sections), 1))

        prompt = prompt_manager.render("section.md", {
            "lesson_title": outline.title,
            "topic": spec.topic,
            "programming_language": spec.programming_language,
            "grade_level": spec.grade_level,
            "section_target_words": per_sec_target,
            "full_outline": full_outline_text,
            "running_summary": running_summary or "This is the first section of the lesson.",
            "section_order": outline_sec.order,
            "section_title": outline_sec.title,
            "section_purpose": outline_sec.purpose,
            "covers_objectives": ", ".join(outline_sec.covers_objectives),
            "covers_objectives_json": ", ".join(f'"{obj}"' for obj in outline_sec.covers_objectives),
            "key_concepts": ", ".join(outline_sec.key_concepts),
            "needs_code_example": "Yes, include at least one clear runnable code example." if outline_sec.needs_code_example else "Optional",
            "teacher_feedback": teacher_feedback or "None - first generation pass",
        })

        response = self.client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            json_mode=True,
            temperature=0.35,
        )

        data = response.parsed_json or {}
        blocks_data = data.get("blocks", [])
        parsed_blocks = []
        for b in blocks_data:
            try:
                parsed_blocks.append(Block(**b))
            except Exception:
                # If block is raw string or malformed, convert to paragraph
                if isinstance(b, dict) and "text" in b:
                    parsed_blocks.append(Block(type="paragraph", text=b["text"]))
                elif isinstance(b, str):
                    parsed_blocks.append(Block(type="paragraph", text=b))

        # Fallback if no blocks were parsed
        if not parsed_blocks:
            parsed_blocks = [
                Block(type="paragraph", text=f"In this section we cover {outline_sec.title} for {spec.programming_language}."),
                Block(type="code", language=spec.programming_language, code=f"# {outline_sec.title}\nprint('Learning {spec.topic}')")
            ]

        # Parse in-situ diagnostic check
        diag_check = None
        diag_raw = data.get("diagnostic_check")
        if diag_raw and isinstance(diag_raw, dict):
            try:
                if not diag_raw.get("concept_tag") and outline_sec.key_concepts:
                    diag_raw["concept_tag"] = outline_sec.key_concepts[0]
                diag_check = DiagnosticQuestion(**diag_raw)
            except Exception:
                pass

        # Parse adaptive remediation blocks
        remediation_blocks = []
        for b in data.get("remediation_blocks", []):
            try:
                remediation_blocks.append(Block(**b))
            except Exception:
                if isinstance(b, dict) and "text" in b:
                    remediation_blocks.append(Block(type="paragraph", text=b["text"]))

        # Parse adaptive extension blocks
        extension_blocks = []
        for b in data.get("extension_blocks", []):
            try:
                extension_blocks.append(Block(**b))
            except Exception:
                if isinstance(b, dict) and "text" in b:
                    extension_blocks.append(Block(type="paragraph", text=b["text"]))

        return Section(
            order=outline_sec.order,
            title=outline_sec.title,
            purpose=outline_sec.purpose,
            covers_objectives=outline_sec.covers_objectives,
            blocks=parsed_blocks,
            diagnostic_check=diag_check,
            remediation_blocks=remediation_blocks,
            extension_blocks=extension_blocks,
        )

    def generate_intro_conclusion(
        self,
        spec: LessonSpec,
        outline: Outline,
        sections: List[Section]
    ) -> Tuple[List[Block], List[Block]]:
        """Pass 3: Generate introduction and conclusion tailored to generated sections."""
        system_prompt = self._get_system_prompt(spec)
        sections_summary = "\n".join(f"- Section {s.order}: {s.title} ({s.purpose})" for s in sections)

        prompt = prompt_manager.render("intro_conclusion.md", {
            "lesson_title": outline.title,
            "subject": spec.subject,
            "topic": spec.topic,
            "programming_language": spec.programming_language,
            "grade_level": spec.grade_level,
            "sections_summary": sections_summary,
        })

        response = self.client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            json_mode=True,
            temperature=0.3,
        )
        data = response.parsed_json or {}

        intro_blocks = []
        for b in data.get("introduction", []):
            try:
                intro_blocks.append(Block(**b))
            except Exception:
                if isinstance(b, dict) and "text" in b:
                    intro_blocks.append(Block(type="paragraph", text=b["text"]))

        conclusion_blocks = []
        for b in data.get("conclusion", []):
            try:
                conclusion_blocks.append(Block(**b))
            except Exception:
                if isinstance(b, dict) and "text" in b:
                    conclusion_blocks.append(Block(type="paragraph", text=b["text"]))

        if not intro_blocks:
            intro_blocks = [Block(type="paragraph", text=f"Welcome to this lesson on {spec.topic} in {spec.programming_language}!")]
        if not conclusion_blocks:
            conclusion_blocks = [Block(type="paragraph", text=f"Congratulations on completing the lesson on {spec.topic}!")]

        return intro_blocks, conclusion_blocks

    def generate_lesson_practice(
        self,
        spec: LessonSpec,
        outline: Outline,
        sections: List[Section]
    ) -> Tuple[List[PuzzleChallenge], List[CodingExercise]]:
        """Generate interactive puzzles (code tracing, Parsons problems) and hands-on coding exercises grounded in actual content."""
        system_prompt = self._get_system_prompt(spec)

        # Build full lesson content text with all prose and actual code snippets taught
        content_parts = []
        for s in sections:
            content_parts.append(f"### Section {s.order}: {s.title}")
            content_parts.append(f"Purpose: {s.purpose}")
            for b in s.blocks:
                if b.type == "paragraph" and b.text:
                    content_parts.append(b.text)
                elif b.type == "code" and b.code:
                    expected = f"\nExpected Output: {b.expected_output}" if b.expected_output else ""
                    content_parts.append(f"```{b.language or spec.programming_language}\n{b.code}\n```{expected}")
                elif b.type == "callout" and b.text:
                    content_parts.append(f"> [{b.callout_type or 'note'}] {b.text}")
                elif b.type == "list" and b.items:
                    for itm in b.items:
                        content_parts.append(f"- {itm}")
            content_parts.append("")

        full_lesson_content = "\n\n".join(content_parts)

        prompt = prompt_manager.render("lesson_practice.md", {
            "subject": spec.subject,
            "topic": spec.topic,
            "programming_language": spec.programming_language,
            "grade_level": spec.grade_level,
            "lesson_title": outline.title,
            "full_lesson_content": full_lesson_content,
        })
        try:
            response = self.client.generate(prompt=prompt, system_prompt=system_prompt, json_mode=True, temperature=0.3)
            data = response.parsed_json or {}

            puzzles = []
            for p in data.get("puzzles", []):
                try:
                    puzzles.append(PuzzleChallenge(**p))
                except Exception:
                    pass

            exercises = []
            for e in data.get("exercises", []):
                try:
                    exercises.append(CodingExercise(**e))
                except Exception:
                    pass

            return puzzles, exercises
        except Exception:
            return [], []

    def generate_segment_assessment(
        self,
        spec: LessonSpec,
        segment: Segment,
        parent_topic_purpose: Optional[str] = None,
    ) -> Optional[SegmentAssessment]:
        """Generate an active-recall micro-check (MCQ, Fill-in-blank, Spot the bug) with spoken TTS prompt grounded in segment content."""
        system_prompt = self._get_system_prompt(spec)
        prompt = prompt_manager.render("segment_assessment.md", {
            "topic": spec.topic,
            "programming_language": spec.programming_language,
            "grade_level": spec.grade_level,
            "segment_title": segment.title,
            "parent_topic_purpose": parent_topic_purpose or segment.topic_title,
            "narration_text": segment.narration_text,
            "attached_code": segment.attached_code or "None displayed in this segment",
        })
        try:
            resp = self.client.generate(prompt=prompt, system_prompt=system_prompt, json_mode=True, temperature=0.3)
            data = resp.parsed_json or {}
            return SegmentAssessment(**data)
        except Exception:
            return None

    def generate_topic_micro_checks(
        self,
        spec: LessonSpec,
        topic_title: str,
        topic_purpose: str,
        segments: List[Segment]
    ) -> Dict[int, SegmentAssessment]:
        """Generate active-recall micro-checks for all segments in a topic in a single batched call."""
        if not segments:
            return {}

        system_prompt = self._get_system_prompt(spec)

        seg_lines = []
        for s in segments:
            code_info = f"\n  Code On-Screen:\n  ```{s.attached_code_language or spec.programming_language}\n  {s.attached_code}\n  ```" if s.attached_code else "\n  Code: None displayed"
            seg_lines.append(
                f"### Segment #{s.order_in_topic}: {s.title}\n"
                f"  Spoken Narration: \"{s.narration_text}\"{code_info}"
            )
        segments_text = "\n\n".join(seg_lines)

        prompt = prompt_manager.render("topic_micro_checks.md", {
            "topic": spec.topic,
            "programming_language": spec.programming_language,
            "grade_level": spec.grade_level,
            "topic_title": topic_title,
            "topic_purpose": topic_purpose or topic_title,
            "segments_text": segments_text,
        })

        try:
            resp = self.client.generate(prompt=prompt, system_prompt=system_prompt, json_mode=True, temperature=0.3)
            data = resp.parsed_json or {}
            assessments_map: Dict[int, SegmentAssessment] = {}

            for itm in data.get("assessments", []):
                try:
                    order = itm.get("order_in_topic")
                    if order is not None:
                        assessments_map[int(order)] = SegmentAssessment(**itm)
                except Exception:
                    pass

            return assessments_map
        except Exception:
            return {}

    def run(
        self,
        spec: LessonSpec,
        progress_callback: Optional[Callable[[str, float], None]] = None,
        teacher_feedback: Optional[str] = None,
    ) -> Tuple[LessonContent, Outline]:
        """Execute full two-pass generation pipeline."""
        if progress_callback:
            progress_callback("Generating lesson outline & mapping objectives...", 0.15)

        outline = self.generate_outline(spec)

        sections: List[Section] = []
        accumulated_concepts: List[str] = []
        running_summary = ""

        total_sections = len(outline.sections)
        for i, outline_sec in enumerate(outline.sections):
            pct = 0.20 + (0.50 * (i / max(total_sections, 1)))
            if progress_callback:
                progress_callback(f"Generating Section {outline_sec.order}: {outline_sec.title}...", pct)

            sec = self.generate_section(
                spec=spec,
                outline=outline,
                outline_sec=outline_sec,
                running_summary=running_summary,
                teacher_feedback=teacher_feedback,
            )
            sections.append(sec)

            # Update accumulated concepts
            accumulated_concepts.extend(outline_sec.key_concepts)

            # Produce narrative bridge if there is a next section
            if i + 1 < total_sections:
                next_sec = outline.sections[i + 1]
                snippet = " ".join([b.text for b in sec.blocks if b.text])
                bridge_data = self.generate_running_bridge(
                    spec=spec,
                    prev_summary=running_summary,
                    section_title=sec.title,
                    key_concepts=accumulated_concepts,
                    section_snippet=snippet,
                    next_title=next_sec.title,
                )
                narrative = bridge_data.get("narrative_bridge", "")
                running_summary = (
                    f"Mastered concepts: {', '.join(set(accumulated_concepts))}.\n"
                    f"Bridge transition: {narrative}"
                )

        if progress_callback:
            progress_callback("Synthesizing engaging Introduction and Conclusion...", 0.75)

        intro_blocks, conclusion_blocks = self.generate_intro_conclusion(spec, outline, sections)

        if progress_callback:
            progress_callback("Crafting interactive puzzles & hands-on coding exercises...", 0.90)

        puzzles, exercises = self.generate_lesson_practice(spec, outline, sections)

        lesson = LessonContent(
            title=outline.title,
            programming_language=spec.programming_language,
            grade_level=spec.grade_level,
            target_duration_minutes=spec.target_duration_minutes or 15,
            introduction=intro_blocks,
            objectives=spec.learning_objectives,
            sections=sections,
            conclusion=conclusion_blocks,
            puzzles=puzzles,
            exercises=exercises,
        )

        if progress_callback:
            progress_callback("Lesson assembly complete!", 1.0)

        return lesson, outline

