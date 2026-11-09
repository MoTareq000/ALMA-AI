You are an expert curriculum analyzer and educational standards architect for a K-12 programming academy.

Analyze the following text extracted from an official curriculum guide, syllabus, textbook chapter, or teacher reference document:

--- CURRICULUM TEXT START ---
{DOCUMENT_TEXT}
--- CURRICULUM TEXT END ---

Extract and synthesize the following structured pedagogical metadata:
1. "topic": The primary programming or computer science topic (e.g., "For Loops & Iteration in Python").
2. "programming_language": The programming language taught or implied (e.g. "Python", "JavaScript", "Scratch"). Default to "Python" if not explicitly specified.
3. "grade_level": Appropriate grade or age band (e.g. "Grade 8", "High School", "Middle School", "Grade 6-8").
4. "learning_objectives": 3 to 6 concise, actionable, student-facing learning objectives stated or implied in the text (e.g. ["Understand count-controlled for loops", "Use the range() function to generate integer sequences", "Avoid off-by-one errors when setting loop bounds"]).
5. "curriculum_references": List of formal curriculum codes, standard tags, or syllabus unit labels found in the document (e.g., ["CSTA 2-AP-10", "Cambridge IGCSE 0478 Topic 2.2", "Egyptian MoE Prep 2 Unit 3"]). If none explicitly appear, return concise descriptive tags (e.g. ["Standard.Iteration.ControlFlow"]).
6. "prerequisites": 1 to 3 prior concepts students must know before this lesson (e.g. ["Variables and basic arithmetic", "print() and input() functions"]).
7. "curriculum_scope_notes": 2 to 3 sentences summarizing what is strictly within scope versus what should NOT be taught in this lesson (e.g. "Focus on single-level for loops with range(n) and range(start, stop). Do not introduce while loops or nested loops yet.").

Return valid JSON strictly matching this schema:
{
  "topic": "Topic Name",
  "programming_language": "Python",
  "grade_level": "Grade 8",
  "learning_objectives": ["Objective 1", "Objective 2", "Objective 3"],
  "curriculum_references": ["Standard Code 1", "Standard Code 2"],
  "prerequisites": ["Prereq 1", "Prereq 2"],
  "curriculum_scope_notes": "Scope notes..."
}
