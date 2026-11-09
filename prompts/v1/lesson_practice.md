You are a senior computer science curriculum educator designing interactive practice puzzles and hands-on coding exercises.

Lesson Context:
- Subject: {SUBJECT}
- Topic: {TOPIC}
- Programming Language: {PROGRAMMING_LANGUAGE}
- Grade Level: {GRADE_LEVEL}
- Lesson Title: {LESSON_TITLE}

=======================================================
ACTUAL LESSON CONTENT TAUGHT TO THE STUDENT:
=======================================================
{FULL_LESSON_CONTENT}

=======================================================
CRITICAL ALIGNMENT & GROUNDING RULES:
=======================================================
1. 100% GROUNDED IN LESSON CONTENT:
   - Every puzzle, code snippet, and coding challenge MUST be directly derived from the concepts, syntax patterns, variables, and examples taught in the lesson content above.
   - Do NOT introduce unintroduced language features, external libraries, or complex syntax that was not taught in this lesson.
   - If the lesson taught `for i in range(1, 6):`, do not test advanced list comprehensions, lambda functions, or while loops unless they were explicitly taught.

2. PUZZLES (Generate 2 puzzles):
   - Puzzle 1: "reorder_lines" (Parsons Problem): Provide 4-6 scrambled lines of code based directly on a code example taught in the lesson. The student arranges them in the correct sequence to solve the task.
   - Puzzle 2: "predict_output" (Code Tracing): A short, grounded code snippet using variables and patterns taught in the lesson where students trace execution and predict the exact printed output.

3. HANDS-ON CODING EXERCISES (Generate 2 exercises):
   - Exercise 1: "easy" (Scaffolded Warmup): A gentle direct application of the core example from the lesson. Starter code has clear fill-in comments.
   - Exercise 2: "medium" (Core Challenge): Applies the concepts to a relatable scenario (e.g., student score tracker, shopping cart, game score).
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
      "description": "Trace variable values as this loop runs:",
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
    }
  ]
}
