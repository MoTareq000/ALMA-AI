from typing import List, Optional, Literal
from pydantic import BaseModel, Field

BlockType = Literal["paragraph", "code", "callout", "list"]
CalloutType = Literal["tip", "warning", "note"]

class Block(BaseModel):
    """A single atomic block of lesson content."""
    type: BlockType = Field(..., description="Type of block: paragraph, code, callout, list")
    text: Optional[str] = Field(default=None, description="Prose text for paragraph or callout")
    callout_type: Optional[CalloutType] = Field(default=None, description="Type of callout (tip, warning, note)")
    items: Optional[List[str]] = Field(default=None, description="Items if type is list")
    language: Optional[str] = Field(default=None, description="Programming language for code block")
    code: Optional[str] = Field(default=None, description="Executable or illustrative code")
    expected_output: Optional[str] = Field(default=None, description="Expected terminal or program output")

from .assessment import PuzzleChallenge, CodingExercise, DiagnosticQuestion

class Section(BaseModel):
    """A pedagogical section containing core instructional blocks and adaptive learning paths."""
    order: int = Field(..., description="1-indexed sequence order")
    title: str = Field(..., description="Title of the section")
    purpose: str = Field(..., description="Educational goal of this section")
    covers_objectives: List[str] = Field(default_factory=list, description="Objectives covered in this section")
    # Core linear path (Standard instruction)
    blocks: List[Block] = Field(default_factory=list, description="Ordered blocks of core instructional content")
    # In-situ diagnostic check to evaluate student mastery of this section
    diagnostic_check: Optional[DiagnosticQuestion] = Field(default=None, description="Formative checkpoint to route learners")
    # Adaptive branch 1: Scaffolded remediation for students who struggle
    remediation_blocks: List[Block] = Field(default_factory=list, description="Scaffolded remediation blocks for struggling learners")
    # Adaptive branch 2: Extension challenges for advanced learners
    extension_blocks: List[Block] = Field(default_factory=list, description="Deep-dive extension blocks for advanced learners")

    def core_words(self) -> int:
        count = 0
        for b in self.blocks:
            if b.type in ("paragraph", "callout") and b.text:
                count += len(b.text.split())
            elif b.type == "list" and b.items:
                count += sum(len(itm.split()) for itm in b.items)
        return count

    def remediation_words(self) -> int:
        count = 0
        for b in self.remediation_blocks:
            if b.type in ("paragraph", "callout") and b.text:
                count += len(b.text.split())
            elif b.type == "list" and b.items:
                count += sum(len(itm.split()) for itm in b.items)
        return count

    def extension_words(self) -> int:
        count = 0
        for b in self.extension_blocks:
            if b.type in ("paragraph", "callout") and b.text:
                count += len(b.text.split())
            elif b.type == "list" and b.items:
                count += sum(len(itm.split()) for itm in b.items)
        return count

class OutlineSection(BaseModel):
    """Section specification inside a lesson outline."""
    order: int
    title: str
    purpose: str
    covers_objectives: List[str] = Field(default_factory=list)
    key_concepts: List[str] = Field(default_factory=list)
    needs_code_example: bool = True
    target_words: Optional[int] = Field(default=None, description="Target prose words for this section")

class Outline(BaseModel):
    """High-level outline generated in Pass 1."""
    title: str
    sections: List[OutlineSection] = Field(default_factory=list)
    target_duration_minutes: Optional[int] = Field(default=15, description="Target narration duration")
    total_target_words: Optional[int] = Field(default=2100, description="Total target words across sections")

class LessonContent(BaseModel):
    """Full structured content of a lesson with adaptive branches."""
    title: str
    programming_language: str
    grade_level: str
    target_duration_minutes: Optional[int] = Field(default=15, description="Target teaching duration in minutes")
    introduction: List[Block] = Field(default_factory=list)
    objectives: List[str] = Field(default_factory=list)
    sections: List[Section] = Field(default_factory=list)
    conclusion: List[Block] = Field(default_factory=list)
    puzzles: List[PuzzleChallenge] = Field(default_factory=list, description="Interactive puzzles & code tracing challenges")
    exercises: List[CodingExercise] = Field(default_factory=list, description="Hands-on coding challenges")

    def total_blocks(self) -> int:
        return len(self.introduction) + sum(len(s.blocks) for s in self.sections) + len(self.conclusion)

    def total_adaptive_blocks(self) -> int:
        return sum(len(s.remediation_blocks) + len(s.extension_blocks) for s in self.sections)

    def total_words(self) -> int:
        """Count prose words in all core non-code blocks."""
        count = 0
        all_blocks = self.introduction + [b for s in self.sections for b in s.blocks] + self.conclusion
        for b in all_blocks:
            if b.type == "paragraph" and b.text:
                count += len(b.text.split())
            elif b.type == "callout" and b.text:
                count += len(b.text.split())
            elif b.type == "list" and b.items:
                count += sum(len(item.split()) for item in b.items)
        return count

    def total_all_words_including_adaptive(self) -> int:
        """Count prose words across core, remediation, and extension branches."""
        core = self.total_words()
        adaptive = sum(s.remediation_words() + s.extension_words() for s in self.sections)
        return core + adaptive
