You are generating deep, adaptive pedagogical content for Section {SECTION_ORDER} of the lesson "{LESSON_TITLE}".

Lesson Context:
- Topic: {TOPIC}
- Programming Language: {PROGRAMMING_LANGUAGE}
- Grade Level: {GRADE_LEVEL}
- Target Word Budget for this section: Approx. {SECTION_TARGET_WORDS} words of core instruction.

Full Outline of the Lesson:
{FULL_OUTLINE}

Concepts & Narrative Introduced in Previous Sections:
{RUNNING_SUMMARY}

Current Section to Generate:
- Order: {SECTION_ORDER}
- Title: {SECTION_TITLE}
- Purpose: {SECTION_PURPOSE}
- Objectives to Cover: {COVERS_OBJECTIVES}
- Key Concepts: {KEY_CONCEPTS}
- Code Example Needed: {NEEDS_CODE_EXAMPLE}

Teacher Feedback / Revision Notes (if any):
{TEACHER_FEEDBACK}

=======================================================
PEDAGOGICAL & ADAPTIVE REQUIREMENTS
=======================================================

1. DEPTH & SUBSTANCE (Do NOT produce shallow content):
   - Write comprehensive, thorough prose totaling approximately {SECTION_TARGET_WORDS} words for the core instruction.
   - Explain how the code works line-by-line, not just high-level descriptions.
   - Structure core blocks in a rich progression:
     a. Engaging introductory paragraph with an intuitive real-world analogy.
     b. Primary runnable code snippet illustrating the syntax clearly.
     c. Explanatory paragraph breaking down the flow of execution and variable states.
     d. Secondary code snippet demonstrating a practical variation or common pattern.
     e. Warning callout ("warning") highlighting a common beginner mistake or pitfall.
     f. Tip callout ("tip") providing a pro-tip or best practice.

2. IN-SITU DIAGNOSTIC CHECKPOINT ("diagnostic_check"):
   - Formative assessment question embedded directly at the end of this section to test whether the student has mastered its key concept.
   - "concept_tag": Must strictly match one of this section's Key Concepts ({KEY_CONCEPTS}) to maintain a consistent mastery tracking taxonomy.
   - Include a "misconception_map" that explicitly explains WHY each incorrect option is wrong and what misunderstanding it reflects.

3. ADAPTIVE REMEDIATION BRANCH ("remediation_blocks"):
   - 2 to 3 scaffolded blocks triggered when a student fails the diagnostic check.
   - Use an alternative visual analogy, a simplified breakdown, or a step-by-step trace table to help struggling learners catch up.

4. ADAPTIVE EXTENSION BRANCH ("extension_blocks"):
   - 2 to 3 enrichment blocks for advanced learners who ace the diagnostic check.
   - Dive deeper into edge cases, language idioms, performance tips, or "what happens if..." challenges.

Output valid, parseable JSON matching this schema. CRITICAL: Any double quotes inside text or code strings must be properly escaped (e.g. \"quoted text\"). Do NOT include unescaped quotes inside string values.
{
  "order": {SECTION_ORDER},
  "title": "{SECTION_TITLE}",
  "purpose": "{SECTION_PURPOSE}",
  "covers_objectives": [{COVERS_OBJECTIVES_JSON}],
  "blocks": [
    {
      "type": "paragraph",
      "text": "Detailed, thorough explanation with intuitive real-world analogy..."
    },
    {
      "type": "code",
      "language": "{PROGRAMMING_LANGUAGE}",
      "code": "executable code snippet",
      "expected_output": "output when run"
    },
    {
      "type": "paragraph",
      "text": "Line-by-line breakdown of how the computer executes this code..."
    },
    {
      "type": "code",
      "language": "{PROGRAMMING_LANGUAGE}",
      "code": "practical variation or pattern snippet",
      "expected_output": "variation output"
    },
    {
      "type": "callout",
      "callout_type": "warning",
      "text": "Common beginner mistake to avoid..."
    },
    {
      "type": "callout",
      "callout_type": "tip",
      "text": "Pro-tip for writing cleaner code..."
    }
  ],
  "diagnostic_check": {
    "concept_tag": "choose one concept from key_concepts",
    "question_text": "Targeted comprehension check on this section's core mechanism...",
    "code_snippet": "code snippet to trace or analyze...",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": "Option B",
    "misconception_map": {
      "Option A": "Confusing the variable with the collection...",
      "Option C": "Off-by-one index assumption...",
      "Option D": "Assuming the loop terminates early..."
    },
    "explanation": "Clear explanation of why Option B is correct."
  },
  "remediation_blocks": [
    {
      "type": "paragraph",
      "text": "Let's slow down and look at this another way with a simple analogy..."
    },
    {
      "type": "code",
      "language": "{PROGRAMMING_LANGUAGE}",
      "code": "simplified scaffolded trace code",
      "expected_output": "step by step output"
    }
  ],
  "extension_blocks": [
    {
      "type": "paragraph",
      "text": "Ready for a deeper dive? Here is how experienced programmers optimize this..."
    },
    {
      "type": "callout",
      "callout_type": "tip",
      "text": "Advanced tip or edge-case behavior to keep in mind..."
    }
  ]
}
