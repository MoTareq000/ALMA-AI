You are a senior computer science curriculum educator designing a standalone interactive practice challenge set for a programming course.

Course Practice Context:
- Topic: {TOPIC}
- Programming Language: {PROGRAMMING_LANGUAGE}
- Grade Level: {GRADE_LEVEL}
- Key Concepts To Cover: {CONCEPTS_TO_COVER}

=======================================================
PRACTICE DESIGN RULES:
=======================================================
1. 100% GROUNDED IN {PROGRAMMING_LANGUAGE} BEST PRACTICES:
   - Provide clean, idiomatic code suitable for a {GRADE_LEVEL} student.
   - Do NOT introduce unneeded third-party libraries; use standard library features.

2. PUZZLES (Generate 2 logic puzzles):
   - Puzzle 1: "reorder_lines" (Parsons Problem): Provide 4-6 scrambled lines of code. The student arranges them in the correct sequence to solve the task.
   - Puzzle 2: "predict_output" (Code Tracing): A short, elegant code snippet using variables and patterns where students trace execution and predict the exact printed output.

3. HANDS-ON CODING CHALLENGES (Generate 3 tiered difficulty exercises for the Dynamic Difficulty Ladder):
   - Exercise 1: "easy" (Foundational Warmup): A gentle direct application of the topic. Starter code is ~80% scaffolded with clear fill-in comments.
   - Exercise 2: "medium" (Core Application Challenge): Applies the concepts to a relatable scenario (e.g., student score tracker, inventory, game score). Starter code has function template and comments (~50% scaffolded).
   - Exercise 3: "hard" (Mastery Challenge): Algorithmic edge-case or multi-step extension that pushes deeper problem solving with minimal starter code (~20% scaffolded).
   - For each exercise:
     * Clear, engaging task description
     * Starter code with clear scaffolding comments
     * 2 progressive hints addressing common beginner misconceptions
     * Clean, working reference solution code in {PROGRAMMING_LANGUAGE}
     * Expected terminal output

Output valid JSON matching this schema:
{
  "puzzles": [
    {
      "puzzle_type": "reorder_lines",
      "title": "Unscramble the Program",
      "description": "Put the scrambled lines in order to...",
      "code_snippet": null,
      "scrambled_items": ["line 1", "line 2", "line 3", "line 4"],
      "correct_order_or_answer": "line 2 -> line 1 -> line 3 -> line 4",
      "explanation": "Step-by-step walkthrough of why this sequence executes correctly..."
    },
    {
      "puzzle_type": "predict_output",
      "title": "Predict the Final Output",
      "description": "Trace variable values as this code runs:",
      "code_snippet": "code snippet here...",
      "scrambled_items": null,
      "correct_order_or_answer": "expected output string",
      "explanation": "Trace breakdown for each iteration..."
    }
  ],
  "exercises": [
    {
      "title": "Warmup Challenge",
      "difficulty": "easy",
      "task_description": "Write a program that...",
      "starter_code": "# Complete the code below\n...",
      "hints": ["Hint 1 addressing syntax...", "Hint 2 addressing logic..."],
      "solution_code": "working code...",
      "expected_output": "Result..."
    },
    {
      "title": "Core Challenge",
      "difficulty": "medium",
      "task_description": "Build a program that...",
      "starter_code": "# Starter code\n...",
      "hints": ["Hint 1...", "Hint 2..."],
      "solution_code": "working code...",
      "expected_output": "Result..."
    },
    {
      "title": "Mastery Edge Challenge",
      "difficulty": "hard",
      "task_description": "Extend your solution to handle edge cases or advanced conditions...",
      "starter_code": "# Starter code\n...",
      "hints": ["Hint 1 addressing edge conditions...", "Hint 2 addressing performance..."],
      "solution_code": "working code...",
      "expected_output": "Result..."
    }
  ]
}
