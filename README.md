# ALMA Academy: AI Lesson Generation Pipeline 🎓

An intelligent, multi-stage pipeline that transforms a teacher's lesson specification into a validated, version-controlled programming lesson, with automated validation and hybrid narration segmentation for future audio voiceovers.

---

## 🌟 Key Architecture & Capabilities

1. **Two-Pass Generation with Narrative Bridges**
   - **Pass 1 (Outline)**: Generates a pedagogical lesson outline and maps every teacher-provided learning objective to specific sections.
   - **Pass 2 (Sequential Sections)**: Generates each instructional section while tracking accumulated key concepts and generating dynamic narrative transitions between sections.
   - **Pass 3 (Intro & Conclusion)**: Synthesizes real-world motivation and celebration blocks tailored to the generated material.

2. **Dynamic Programming Language Selection**
   - Seamlessly generates lessons for any language: **Python, JavaScript, Java, C++, C#, TypeScript, HTML/CSS, Go, Rust, Ruby, PHP, Scratch, SQL**, or custom user-defined languages.

3. **Streamlined Validation Suite**
   - **Schema Validator**: Enforces Pydantic structural types and serialization integrity.
   - **Structure Validator**: Checks for non-empty sections, 100% objective coverage, absence of placeholder tokens (`TODO`, `TBD`, etc.), and valid code blocks.
   - **Independent LLM Quality Judge**: Evaluates pedagogical clarity, age-appropriateness, and technical accuracy using an independent model family (e.g. `qwen/qwen3.8-27b`).

4. **Interactive Teacher Workbench (Streamlit)**
   - **Live Preview**: Polished rendering of prose, syntax-highlighted code blocks, tip/note callouts, and objectives.
   - **In-Place Teacher Editor**: Allows teachers to edit titles, prose, purposes, and code blocks directly.
   - **Append-Only Versioning**: Edits create immutable new versions (`v1`, `v2`, `v3`), preserving revision history.
   - **Teacher Actions**: Approve lesson, reject with reason, or request AI regeneration with custom guidance notes.

5. **Audio Narration & Topic Segmentation**
   - Breaks approved lessons into topics and atomic ~45–60 second narration segments (~105–140 words at 140 WPM).
   - Preserves code demonstration attachments without splitting code blocks.

6. **In-Memory Store with JSON Portability**
   - Zero-database setup: keeps lessons in active memory with full export and import of sessions to JSON.

---

## 🚀 Quickstart Guide

### 1. Requirements
- Python 3.10+
- Groq API Key (or OpenRouter API Key)

### 2. Configure Environment
Copy `.env.example` to `.env` and set your key:
```bash
GROQ_API_KEY=gsk_your_groq_key_here
```

### 3. Run the Test Suite
```bash
python run_tests.py
```

### 4. Launch the Interactive Workbench
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 📂 Project Structure

```
lesson-gen/
├── app.py                     # Streamlit Interactive Review Workbench
├── run_tests.py               # Test runner
├── .env.example               # Environment variables template
├── pyproject.toml             # Project dependencies and packaging
├── prompts/v1/                # Versioned markdown prompts
│   ├── system.md
│   ├── outline.md
│   ├── section.md
│   ├── bridge.md
│   ├── intro_conclusion.md
│   ├── lesson_practice.md
│   ├── segment_assessment.md
│   └── judge_quality.md
├── src/alma_lessons/          # Core implementation package
│   ├── config.py              # Central settings
│   ├── domain/                # Pydantic domain models
│   │   ├── spec.py            # LessonSpec
│   │   ├── content.py         # Block, Section, LessonContent
│   │   ├── assessment.py      # DiagnosticQuestion, SegmentAssessment, Puzzles
│   │   ├── state.py           # 6-State lifecycle machine
│   │   └── segment.py         # Segment, LessonSegmentation
│   ├── llm/                   # Multi-provider client abstraction
│   │   ├── interface.py       # BaseLLMClient
│   │   ├── groq_client.py     # Groq SDK adapter
│   │   ├── openrouter_client.py # OpenRouter adapter
│   │   └── fake_client.py     # Deterministic offline mock
│   ├── generation/            # Two-pass generation pipeline
│   │   ├── prompts.py         # Prompt loader with {PLACEHOLDER} parsing
│   │   └── pipeline.py        # Outline -> Sections -> Bridges -> Intro/Concl
│   ├── validation/            # Verification & audit
│   │   ├── schema_validator.py
│   │   ├── structure_validator.py
│   │   ├── llm_judge.py
│   │   └── runner.py
│   ├── segmentation/          # Narration chunking
│   │   └── segmenter.py       # BasicLessonSegmenter
│   └── storage/               # Memory store & JSON export/import
│       └── memory_store.py
└── tests/                     # Unit & integration tests
    ├── test_domain.py
    ├── test_generation.py
    ├── test_validation.py
    ├── test_segmentation.py
    └── test_storage.py
```
