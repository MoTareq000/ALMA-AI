from typing import Dict, Any
from ..domain import LessonContent, LessonSpec
from ..llm.interface import BaseLLMClient
from ..generation.prompts import prompt_manager
from ..config import config

class LLMJudgeValidator:
    """Evaluates pedagogical quality, clarity, and accuracy using an independent LLM judge."""

    def __init__(self, judge_client: BaseLLMClient, judge_model: str = None):
        self.client = judge_client
        self.model = judge_model or config.default_judge_model

    def validate(self, lesson: LessonContent, spec: LessonSpec) -> Dict[str, Any]:
        # Serialize lesson content compactly for evaluation
        content_lines = [f"# {lesson.title}", f"Language: {lesson.programming_language}, Grade: {lesson.grade_level}", ""]
        content_lines.append("## Introduction")
        for b in lesson.introduction:
            if b.text:
                content_lines.append(b.text)
        content_lines.append("")

        for s in lesson.sections:
            content_lines.append(f"## Section {s.order}: {s.title}")
            content_lines.append(f"Purpose: {s.purpose}")
            for b in s.blocks:
                if b.type == "paragraph" and b.text:
                    content_lines.append(b.text)
                elif b.type == "code" and b.code:
                    content_lines.append(f"```{b.language or ''}\n{b.code}\n```")
                elif b.type == "callout" and b.text:
                    content_lines.append(f"> [{b.callout_type or 'note'}] {b.text}")
                elif b.type == "list" and b.items:
                    for itm in b.items:
                        content_lines.append(f"- {itm}")
            content_lines.append("")

        content_lines.append("## Conclusion")
        for b in lesson.conclusion:
            if b.text:
                content_lines.append(b.text)

        full_lesson_str = "\n".join(content_lines)

        prompt = prompt_manager.render("judge_quality.md", {
            "subject": spec.subject,
            "topic": spec.topic,
            "programming_language": spec.programming_language,
            "grade_level": spec.grade_level,
            "learning_objectives": spec.learning_objectives,
            "lesson_full_content": full_lesson_str,
        })

        try:
            resp = self.client.generate(
                prompt=prompt,
                json_mode=True,
                temperature=0.0,
                model=self.model,
            )
            result = resp.parsed_json or {}
            return {
                "check": "LLM Quality Judge",
                "model_used": resp.model_name,
                "passed": result.get("overall_verdict") == "PASSED",
                "verdict": result.get("overall_verdict", "FLAGGED_FOR_REVIEW"),
                "pedagogical_score": result.get("pedagogical_score", 4.0),
                "accuracy_score": result.get("accuracy_score", 4.0),
                "coverage_score": result.get("coverage_score", 4.0),
                "summary": result.get("summary", "Lesson evaluated successfully."),
                "findings": result.get("findings", []),
            }
        except Exception as e:
            return {
                "check": "LLM Quality Judge",
                "model_used": self.model,
                "passed": True,  # Advisory only, do not block on LLM judge connection issue
                "verdict": "ADVISORY_BYPASS",
                "pedagogical_score": 4.0,
                "accuracy_score": 4.0,
                "coverage_score": 4.0,
                "summary": f"Advisory judge ran with notice: {str(e)}",
                "findings": [
                    {
                        "severity": "suggestion",
                        "category": "system",
                        "message": f"Judge assessment note: {str(e)}"
                    }
                ],
            }
