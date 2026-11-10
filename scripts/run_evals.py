#!/usr/bin/env python3
"""ALMA Academy AI Lesson Evaluation Harness.

Runs test lesson specifications through the lesson generation and segmentation pipeline,
recording quality metrics, validation results, token usage, and latency.

Default provider is 'fake' (cost-free). Real LLM providers require explicit --confirm-spend.
"""

import sys
import json
import time
import argparse
import ast
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add src to pythonpath
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from alma_lessons.domain import LessonSpec
from alma_lessons.generation.pipeline import LessonGenerationPipeline
from alma_lessons.segmentation.segmenter import BasicLessonSegmenter
from alma_lessons.validation.runner import ValidationRunner
from alma_lessons.llm.fake_client import FakeLLMClient
from alma_lessons.api.deps import get_llm_client

PLACEHOLDER_REGEX = re.compile(
    r"\b(TODO|TBD|FIXME|LOREM IPSUM|\[INSERT.*?\]|\[PLACEHOLDER.*?\])\b",
    re.IGNORECASE
)


class EvalClientTracker:
    """Wrapper around an LLM client to record per-call token usage, latency, and call count."""

    def __init__(self, inner_client):
        self.inner = inner_client
        self.calls: List[Dict[str, Any]] = []
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    def generate(self, *args, **kwargs):
        resp = self.inner.generate(*args, **kwargs)
        self.total_prompt_tokens += getattr(resp, "prompt_tokens", 0)
        self.total_completion_tokens += getattr(resp, "completion_tokens", 0)
        self.calls.append({
            "model": getattr(resp, "model_name", "unknown"),
            "prompt_tokens": getattr(resp, "prompt_tokens", 0),
            "completion_tokens": getattr(resp, "completion_tokens", 0),
            "latency_ms": getattr(resp, "latency_ms", 0.0),
        })
        return resp

    def reset_stats(self):
        self.calls = []
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0


def evaluate_spec(
    spec_path: Path,
    tracker: EvalClientTracker,
    validator: ValidationRunner,
    segmenter: BasicLessonSegmenter
) -> Dict[str, Any]:
    with open(spec_path, "r", encoding="utf-8") as f:
        spec_dict = json.load(f)

    spec = LessonSpec(**spec_dict)
    tracker.reset_stats()

    start_time = time.perf_counter()
    pipeline = LessonGenerationPipeline(llm_client=tracker)
    lesson, outline = pipeline.run(spec)
    segmentation = segmenter.segment_lesson(lesson, spec=spec)
    elapsed_sec = round(time.perf_counter() - start_time, 3)

    # 1. Validation report
    val_report = validator.run(lesson, spec)

    # 2. Narration segment word counts vs target 105-140 words
    all_segments = []
    for topic_seg in segmentation.topics:
        all_segments.extend(topic_seg.segments)

    segment_word_counts = [len(s.narration_text.split()) for s in all_segments]
    in_target_range = [w for w in segment_word_counts if 105 <= w <= 140]
    avg_words = round(sum(segment_word_counts) / max(len(segment_word_counts), 1), 1)

    # 3. Python code syntax check using ast.parse (skip other languages)
    python_ast_errors = []
    python_blocks_count = 0
    if spec.programming_language.lower() == "python":
        all_blocks = lesson.introduction + [b for s in lesson.sections for b in s.blocks] + lesson.conclusion
        for i, b in enumerate(all_blocks):
            if b.type == "code" and b.code:
                python_blocks_count += 1
                try:
                    ast.parse(b.code)
                except SyntaxError as e:
                    python_ast_errors.append(f"Block #{i+1}: {e.msg} (line {e.lineno})")

    # 4. Objective coverage
    covered_objectives = set()
    for s in lesson.sections:
        for obj in s.covers_objectives:
            covered_objectives.add(obj.strip().lower())
    uncovered_objs = [
        target_obj for target_obj in spec.learning_objectives
        if not any(target_obj.strip().lower() in cov or cov in target_obj.strip().lower() for cov in covered_objectives)
    ]
    objective_coverage_pct = round(
        ((len(spec.learning_objectives) - len(uncovered_objs)) / max(len(spec.learning_objectives), 1)) * 100.0, 1
    )

    # 5. Placeholder detection
    placeholders_found = []
    all_blocks = lesson.introduction + [b for s in lesson.sections for b in s.blocks] + lesson.conclusion
    for i, b in enumerate(all_blocks):
        text_to_check = (b.text or "") + " " + " ".join(b.items or []) + " " + (b.code or "")
        matches = PLACEHOLDER_REGEX.findall(text_to_check)
        if matches:
            placeholders_found.extend(matches)

    return {
        "spec_file": spec_path.name,
        "topic": spec.topic,
        "language": spec.language,
        "programming_language": spec.programming_language,
        "grade_level": spec.grade_level,
        "status": val_report.get("overall_status"),
        "has_blocking_errors": val_report.get("has_blocking_errors"),
        "errors": val_report.get("errors", []),
        "warnings": val_report.get("warnings", []),
        "objective_coverage_pct": objective_coverage_pct,
        "uncovered_objectives": uncovered_objs,
        "placeholders_count": len(placeholders_found),
        "total_segments": len(all_segments),
        "avg_segment_words": avg_words,
        "segments_in_target_105_140": len(in_target_range),
        "python_blocks_count": python_blocks_count,
        "python_ast_errors": python_ast_errors,
        "elapsed_sec": elapsed_sec,
        "llm_calls_count": len(tracker.calls),
        "total_prompt_tokens": tracker.total_prompt_tokens,
        "total_completion_tokens": tracker.total_completion_tokens,
        "total_tokens": tracker.total_prompt_tokens + tracker.total_completion_tokens,
    }


def generate_markdown_summary(results: List[Dict[str, Any]]) -> str:
    lines = [
        "# Evaluation Results Summary",
        "",
        "| Spec | Lang | Grade | Status | Obj Cov % | Segments | Avg Words | Python AST Errors | Latency (s) | Total Tokens |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        ast_err_str = str(len(r["python_ast_errors"])) if r["programming_language"].lower() == "python" else "N/A"
        lines.append(
            f"| `{r['spec_file']}` | {r['programming_language']} ({r['language']}) | {r['grade_level']} | "
            f"**{r['status']}** | {r['objective_coverage_pct']}% | {r['total_segments']} | {r['avg_segment_words']} | "
            f"{ast_err_str} | {r['elapsed_sec']}s | {r['total_tokens']} |"
        )
    return "\n".join(lines)


def compare_runs(current_file: Path, prev_file: Path):
    with open(current_file, "r", encoding="utf-8") as f:
        curr = json.load(f)
    with open(prev_file, "r", encoding="utf-8") as f:
        prev = json.load(f)

    curr_res = {r["spec_file"]: r for r in curr.get("results", [])}
    prev_res = {r["spec_file"]: r for r in prev.get("results", [])}

    print("\n=== Regression Comparison ===")
    print(f"Current:  {current_file.name} (Provider: {curr.get('provider')})")
    print(f"Previous: {prev_file.name} (Provider: {prev.get('provider')})")
    print("-" * 80)
    print(f"{'Spec File':<35} | {'Metric':<20} | {'Previous':<10} | {'Current':<10} | {'Diff'}")
    print("-" * 80)

    for spec_name, c in curr_res.items():
        if spec_name not in prev_res:
            continue
        p = prev_res[spec_name]

        # Check status regression
        if p["status"] == "PASSED" and c["status"] != "PASSED":
            print(f"{spec_name:<35} | {'Status':<20} | {p['status']:<10} | {c['status']:<10} | REGRESSION")

        # Check coverage
        cov_diff = c["objective_coverage_pct"] - p["objective_coverage_pct"]
        if abs(cov_diff) > 0.01:
            print(f"{spec_name:<35} | {'Obj Coverage %':<20} | {p['objective_coverage_pct']:<10} | {c['objective_coverage_pct']:<10} | {cov_diff:+.1f}%")

        # Check latency
        lat_diff = round(c["elapsed_sec"] - p["elapsed_sec"], 2)
        print(f"{spec_name:<35} | {'Latency (sec)':<20} | {p['elapsed_sec']:<10} | {c['elapsed_sec']:<10} | {lat_diff:+.2f}s")


def main():
    parser = argparse.ArgumentParser(description="ALMA AI Evaluation Harness")
    parser.add_argument("--provider", default="fake", choices=["fake", "gemini", "groq", "openrouter"], help="LLM Provider")
    parser.add_argument("--confirm-spend", action="store_true", help="Explicit confirmation required to use paid LLM APIs")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of specs to evaluate")
    parser.add_argument("--compare", type=str, default=None, help="Path to previous eval json result to compare regressions")
    parser.add_argument("--specs-dir", default=str(PROJECT_ROOT / "evals" / "specs"), help="Path to specs directory")
    args = parser.parse_args()

    # Security guard: Never call real LLM unless explicitly opted in with --confirm-spend
    if args.provider != "fake" and not args.confirm_spend:
        print(f"Error: Running evals against real LLM provider '{args.provider}' requires the explicit --confirm-spend flag.")
        print("This prevents accidental token expenditure. Re-run with --confirm-spend if intentional.")
        sys.exit(1)

    # Initialize client
    if args.provider == "fake":
        client = FakeLLMClient()
    else:
        client = get_llm_client(provider=args.provider)

    tracker = EvalClientTracker(client)
    validator = ValidationRunner()
    segmenter = BasicLessonSegmenter()

    specs_dir = Path(args.specs_dir)
    spec_files = sorted(specs_dir.glob("*.json"))
    if args.limit:
        spec_files = spec_files[:args.limit]

    print(f"Starting evaluation of {len(spec_files)} specs with provider '{args.provider}'...")
    results = []
    for spec_file in spec_files:
        print(f"Evaluating {spec_file.name}...", end="", flush=True)
        r = evaluate_spec(spec_file, tracker, validator, segmenter)
        results.append(r)
        print(f" Done ({r['status']}, {r['elapsed_sec']}s)")

    # Save results
    results_dir = PROJECT_ROOT / "evals" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_json = results_dir / f"{timestamp}.json"
    out_md = results_dir / f"{timestamp}_summary.md"

    summary_data = {
        "timestamp": timestamp,
        "provider": args.provider,
        "spec_count": len(results),
        "results": results,
    }
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)

    md_content = generate_markdown_summary(results)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(md_content)

    print("\nResults saved to:")
    print(f"  JSON: {out_json}")
    print(f"  Summary Markdown: {out_md}\n")
    print(md_content)

    if args.compare:
        compare_runs(out_json, Path(args.compare))


if __name__ == "__main__":
    main()

