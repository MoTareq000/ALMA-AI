You are crafting the Introduction and Conclusion blocks for the completed programming lesson: "{LESSON_TITLE}".

Context:
- Subject: {SUBJECT}
- Topic: {TOPIC}
- Programming Language: {PROGRAMMING_LANGUAGE}
- Grade Level: {GRADE_LEVEL}

Sections Actually Taught in This Lesson:
{SECTIONS_SUMMARY}

Instructions:
1. Introduction: Create 2-3 engaging introductory blocks (e.g. an exciting real-world hook paragraph, an introductory tip or note callout) that spark curiosity about why this concept matters.
2. Conclusion: Create 2-3 concluding blocks summarizing the core takeaway, celebrating what they built/learned, and suggesting a challenge or next step.
3. Available block types: "paragraph", "callout", "list".

Output valid JSON:
{
  "introduction": [
    {
      "type": "paragraph",
      "text": "Exciting hook introducing the topic..."
    },
    {
      "type": "callout",
      "callout_type": "note",
      "text": "Why this matters in real software engineering..."
    }
  ],
  "conclusion": [
    {
      "type": "paragraph",
      "text": "Wrap-up summary of everything learned today..."
    },
    {
      "type": "callout",
      "callout_type": "tip",
      "text": "Try this challenge on your own next..."
    }
  ]
}
