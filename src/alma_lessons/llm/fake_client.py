from typing import Optional, Dict, Any
from .interface import BaseLLMClient, LLMResponse

class FakeLLMClient(BaseLLMClient):
    """Deterministic fake LLM client for testing and offline scenarios."""

    def __init__(self, responses: Optional[Dict[str, Dict[str, Any]]] = None):
        self.responses = responses or {}
        self.call_history = []

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = True,
        temperature: float = 0.3,
        model: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        self.call_history.append({"prompt": prompt, "system_prompt": system_prompt})

        # Match response based on keywords or return default
        parsed = None
        content = "{}"
        if "interactive educational game designer" in prompt.lower() or "micro-check question" in prompt.lower():
            parsed = {
                "question_type": "mcq",
                "spoken_tts_prompt": "Quick check! Which function did we just use to generate a sequence of numbers?",
                "question_text": "Which function generates a sequence of numbers in Python?",
                "code_snippet": "for i in ___(5):\n    print(i)",
                "options": ["range()", "sequence()", "list_nums()", "count()"],
                "correct_answer": "range()",
                "explanation": "The range() function produces an iterable sequence of numbers in Python."
            }
        elif "practice puzzles and hands-on coding exercises" in prompt.lower() or "senior computer science educator" in prompt.lower():
            parsed = {
                "puzzles": [
                    {
                        "puzzle_type": "reorder_lines",
                        "title": "Unscramble the Countdown Loop",
                        "description": "Arrange these lines in order so the program counts down from 3 to 1:",
                        "code_snippet": None,
                        "scrambled_items": [
                            "for i in range(3, 0, -1):",
                            "print('Blastoff!')",
                            "print(i)"
                        ],
                        "correct_order_or_answer": "for i in range(3, 0, -1): -> print(i) -> print('Blastoff!')",
                        "explanation": "First start the loop, indent the print(i) inside the loop, and print 'Blastoff!' after the loop finishes."
                    },
                    {
                        "puzzle_type": "predict_output",
                        "title": "Trace the Accumulator",
                        "description": "What will this loop output when executed?",
                        "code_snippet": "total = 0\nfor n in [2, 4]:\n    total += n\nprint(total)",
                        "scrambled_items": None,
                        "correct_order_or_answer": "6",
                        "explanation": "In iteration 1: total = 0 + 2 = 2. In iteration 2: total = 2 + 4 = 6."
                    }
                ],
                "exercises": [
                    {
                        "title": "Warmup: Multiples of Three",
                        "difficulty": "easy",
                        "task_description": "Print the first 4 multiples of 3 starting from 3 (3, 6, 9, 12) using a for loop.",
                        "starter_code": "# Use range() with a step of 3\nfor num in range(3, ___ , ___):\n    print(num)",
                        "hints": [
                            "Remember that range(start, stop, step) excludes the stop number.",
                            "To include 12, your stop value should be at least 13 or 15."
                        ],
                        "solution_code": "for num in range(3, 15, 3):\n    print(num)",
                        "expected_output": "3\n6\n9\n12"
                    },
                    {
                        "title": "Core Challenge: Shopping Cart Total",
                        "difficulty": "medium",
                        "task_description": "Given a list of item prices, calculate the total price and apply a $5 discount if the total exceeds $50.",
                        "starter_code": "prices = [15.0, 22.5, 18.0]\ntotal = 0.0\n# Write your loop here\n",
                        "hints": [
                            "Use a running total variable initialized to 0.",
                            "Add each price in the loop, then check if total > 50 with an if statement."
                        ],
                        "solution_code": "prices = [15.0, 22.5, 18.0]\ntotal = sum(prices)\nif total > 50:\n    total -= 5.0\nprint(f'Final: ${total:.2f}')",
                        "expected_output": "Final: $50.50"
                    }
                ]
            }
        elif "evaluation rubric" in prompt.lower() or "pedagogical evaluator" in prompt.lower():
            parsed = {
                "overall_verdict": "PASSED",
                "pedagogical_score": 4.8,
                "accuracy_score": 4.9,
                "coverage_score": 4.7,
                "summary": "Excellent structured progression with clear real-world examples and accurate syntax.",
                "findings": [
                    {
                        "severity": "praise",
                        "category": "clarity",
                        "message": "Clear explanation of loop concept with intuitive analogies."
                    }
                ]
            }
        elif "introduction and conclusion" in prompt.lower() or "synthesizing engaging" in prompt.lower():
            parsed = {
                "introduction": [
                    {
                        "type": "paragraph",
                        "text": "Welcome to an essential superpower in programming: automating repetitive actions effortlessly with loops!"
                    }
                ],
                "conclusion": [
                    {
                        "type": "paragraph",
                        "text": "Great job! You now understand how to repeat tasks in code without writing duplicate lines."
                    }
                ]
            }
        elif "summarizing the educational progression" in prompt.lower() or "narrative_bridge" in prompt.lower():
            parsed = {
                "narrative_bridge": "Students have now grasped basic iteration. Next, we will unlock the power of numeric sequences with range().",
                "mastered_concepts": ["iteration", "loop body"]
            }
        elif "lesson outline" in prompt.lower() or "design a structured lesson outline" in prompt.lower():
            parsed = {
                "title": "Mastering For Loops in Python",
                "sections": [
                    {
                        "order": 1,
                        "title": "Introduction to Iteration",
                        "purpose": "Explain why loops exist and basic for loop syntax",
                        "covers_objectives": ["Understand loop concept"],
                        "key_concepts": ["iteration", "for loop", "syntax"],
                        "needs_code_example": True
                    },
                    {
                        "order": 2,
                        "title": "Using the range() Function",
                        "purpose": "Teach counting and step parameters",
                        "covers_objectives": ["Use range with for loops"],
                        "key_concepts": ["range", "start, stop, step"],
                        "needs_code_example": True
                    }
                ]
            }
        elif "generating the content for section" in prompt.lower() or "section" in prompt.lower():
            parsed = {
                "order": 1,
                "title": "Introduction to Iteration",
                "purpose": "Explain why loops exist and basic for loop syntax",
                "covers_objectives": ["Understand loop concept"],
                "blocks": [
                    {
                        "type": "paragraph",
                        "text": "Imagine you have to print numbers from 1 to 100. Writing print() 100 times is exhausting! This is where loops shine."
                    },
                    {
                        "type": "code",
                        "language": "Python",
                        "code": "for i in range(1, 4):\n    print('Count:', i)",
                        "expected_output": "Count: 1\nCount: 2\nCount: 3"
                    },
                    {
                        "type": "callout",
                        "callout_type": "tip",
                        "text": "Remember that Python uses indentation to know what is inside the loop body."
                    }
                ],
                "diagnostic_check": {
                    "concept_tag": "iteration",
                    "question_text": "What does the loop variable 'i' represent during each iteration?",
                    "code_snippet": "for i in range(1, 4):\n    print(i)",
                    "options": [
                        "The current item/number from the sequence",
                        "The total number of iterations remaining",
                        "The memory address of the loop",
                        "A constant value that never changes"
                    ],
                    "correct_answer": "The current item/number from the sequence",
                    "misconception_map": {
                        "The total number of iterations remaining": "Confusing the loop variable with a countdown counter",
                        "The memory address of the loop": "Overcomplicating the role of basic loop variables",
                        "A constant value that never changes": "Missing that loop variables are updated each iteration"
                    },
                    "explanation": "In Python, the loop variable automatically takes on the value of the next element in the iterable on every cycle."
                },
                "remediation_blocks": [
                    {
                        "type": "paragraph",
                        "text": "Let's visualize a for loop like a conveyor belt. Each item on the belt arrives one at a time for you to inspect."
                    },
                    {
                        "type": "code",
                        "language": "Python",
                        "code": "# Step-by-step conveyor belt simulation\nfor item in ['apple', 'banana']:\n    print('Inspecting:', item)",
                        "expected_output": "Inspecting: apple\nInspecting: banana"
                    }
                ],
                "extension_blocks": [
                    {
                        "type": "paragraph",
                        "text": "Pro-tip for advanced programmers: You can also use enumerate() when you need both the index and the item together."
                    },
                    {
                        "type": "callout",
                        "callout_type": "tip",
                        "text": "Using enumerate(sequence) prevents the need for manual counter variables."
                    }
                ]
            }
        else:
            parsed = {"status": "default_mock"}

        import json
        content = json.dumps(parsed)

        return LLMResponse(
            content=content,
            parsed_json=parsed,
            model_name="fake-model",
            prompt_tokens=100,
            completion_tokens=150,
            latency_ms=12.5,
        )
