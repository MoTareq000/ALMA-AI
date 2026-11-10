from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field

QuestionType = Literal["mcq", "fill_in_the_blank", "identify_the_error"]
PuzzleType = Literal["code_trace", "reorder_lines", "predict_output"]
ExerciseDifficulty = Literal["easy", "medium", "hard"]

class DiagnosticQuestion(BaseModel):
    """In-situ formative check embedded in a section to diagnose understanding and route students adaptively."""
    concept_tag: Optional[str] = Field(
        default=None,
        description="The canonical concept tag assessed (strictly chosen from section key_concepts)"
    )
    question_text: str = Field(..., description="The diagnostic question presented to the learner")
    code_snippet: Optional[str] = Field(default=None, description="Illustrative code snippet for the question")
    options: List[str] = Field(default_factory=list, description="Multiple choice answer choices")
    correct_answer: str = Field(..., description="The correct answer string")
    misconception_map: Dict[str, str] = Field(
        default_factory=dict,
        description="Maps each wrong choice to the specific misconception/error the student made"
    )
    explanation: str = Field(..., description="Detailed explanation of the correct logic")

class SegmentAssessment(BaseModel):
    """Micro-check question appearing right after a ~45-60s narration segment."""
    question_type: QuestionType = Field(..., description="Type: mcq, fill_in_the_blank, identify_the_error")
    spoken_tts_prompt: str = Field(..., description="Conversational audio prompt read aloud by the TTS narrator")
    question_text: str = Field(..., description="Written question displayed on screen")
    code_snippet: Optional[str] = Field(default=None, description="Code snippet with '___' blank or containing a bug")
    options: Optional[List[str]] = Field(default=None, description="Options for MCQ or fill-in-the-blank choices")
    correct_answer: str = Field(..., description="The correct answer string")
    explanation: str = Field(..., description="Pedagogical explanation of why this answer is correct")

class PuzzleChallenge(BaseModel):
    """Logic or code-tracing puzzle consolidating concepts across sections."""
    puzzle_type: PuzzleType = Field(..., description="Puzzle style: code_trace, reorder_lines, predict_output")
    title: str = Field(..., description="Engaging title for the puzzle")
    description: str = Field(..., description="Instructions and context for the puzzle")
    code_snippet: Optional[str] = Field(default=None, description="Code snippet to trace or reorder")
    scrambled_items: Optional[List[str]] = Field(default=None, description="Scrambled lines of code for reordering")
    correct_order_or_answer: str = Field(..., description="Target output or correct line sequence")
    explanation: str = Field(..., description="Step-by-step walkthrough explaining the logic")

class CodingExercise(BaseModel):
    """Hands-on programming exercise with scaffolded starter code and solution."""
    title: str = Field(..., description="Exercise title")
    difficulty: ExerciseDifficulty = Field(default="medium", description="easy, medium, or hard")
    task_description: str = Field(..., description="Clear real-world programming problem statement")
    starter_code: str = Field(..., description="Starter code template for the student to build upon")
    hints: List[str] = Field(default_factory=list, description="Progressive hints if student is stuck")
    solution_code: str = Field(..., description="Complete reference solution code")
    expected_output: str = Field(..., description="Expected output from running the solution")
