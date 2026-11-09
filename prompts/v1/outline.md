Design a comprehensive, adaptive-ready lesson outline for a programming class.

Lesson Specification:
- Subject: {SUBJECT}
- Topic: {TOPIC}
- Programming Language: {PROGRAMMING_LANGUAGE}
- Grade Level: {GRADE_LEVEL}
- Desired Depth: {DESIRED_DEPTH}
- Target Narration Duration: {TARGET_DURATION_MINUTES} minutes (Approx. {TOTAL_TARGET_WORDS} words of spoken instruction at 140 WPM)
- Learning Objectives:
{LEARNING_OBJECTIVES}
- Prerequisites: {PREREQUISITES}
- Curriculum References: {CURRICULUM_REFERENCES}
- Curriculum Scope Constraints: {CURRICULUM_SCOPE_NOTES}
- Teacher Special Instructions: {ADDITIONAL_INSTRUCTIONS}

Pedagogical & Adaptive Architecture Requirements:
1. Divide the lesson into 4 to 6 logical, comprehensive instructional sections to properly cover the topic in sufficient depth for {TARGET_DURATION_MINUTES} minutes of teaching. Do NOT create an overly short lesson.
2. Every single learning objective listed above MUST be covered in at least one section's "covers_objectives" list. Strictly adhere to any Curriculum Scope Constraints.
3. Design a progressive pedagogical scaffold:
   - Section 1: Motivation, mental model, and why the concept exists.
   - Section 2: Core syntax, execution flow, and line-by-line breakdown.
   - Section 3: Practical real-world patterns and data manipulation.
   - Section 4: Advanced variations (e.g. range step/start, collections, accumulation).
   - Section 5: Common pitfalls, off-by-one errors, and debugging (crucial for adaptive diagnosis).
4. For each section, specify an appropriate "target_words" budget (e.g., 350 to 450 words) such that the sum approaches {TOTAL_TARGET_WORDS}.
5. Output valid JSON matching this schema:
{
  "title": "Clear, engaging lesson title",
  "target_duration_minutes": {TARGET_DURATION_MINUTES},
  "total_target_words": {TOTAL_TARGET_WORDS},
  "sections": [
    {
      "order": 1,
      "title": "Section Title",
      "purpose": "Pedagogical goal and mental model of this section",
      "covers_objectives": ["Objective text or id"],
      "key_concepts": ["concept1", "concept2"],
      "needs_code_example": true,
      "target_words": 400
    }
  ]
}
