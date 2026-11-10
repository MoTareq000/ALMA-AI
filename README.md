# ALMA Academy: AI Lesson Generation & Runtime Platform 🎓

An enterprise, multi-stage pipeline and adaptive runtime engine that transforms teacher lesson specifications into validated, version-controlled programming curricula with automated structural checks, real-time student adaptive runtime telemetry, and hybrid audio narration segmentation.

---

## 🌟 Key Architecture & Capabilities

1. **Two-Pass Generation with Narrative Bridges**
   - **Pass 1 (Outline)**: Synthesizes a structured outline mapping every learning objective to instructional sections with time/word budgeting.
   - **Pass 2 (Sequential Sections & Bridges)**: Generates detailed pedagogical sections while tracking accumulated mastery concepts and creating narrative transitions between sections.
   - **Pass 3 (Intro, Conclusion & Practice)**: Generates motivational introductions, summaries, active-recall micro-checks, code-tracing puzzles, and coding exercises.

2. **Deterministic Validation Suite**
   - **Schema Validator**: Enforces Pydantic structural integrity and type safety.
   - **Structure Validator**: Verifies 100% learning objective coverage, non-empty instructional blocks, absence of placeholder tokens (`TODO`, `TBD`, `[INSERT...]`), and syntax-valid code blocks.

3. **Audio Narration & Topic Segmentation**
   - Partitions approved lessons into topic units and atomic ~45–60 second narration segments (~105–140 words at 140 WPM).
   - Preserves code demonstration attachments without splitting snippets.

4. **Fail-Fast Dual Storage Layer**
   - Pluggable storage architecture: connects to MongoDB (aligned with ALMA Mongoose schemas) or falls back to in-memory store for local testing.
   - Set `REQUIRE_MONGODB=true` to fail fast at startup if MongoDB is unreachable, preventing accidental degraded in-memory states in production.
   - `/api/v1/health` reports the active database adapter and reports `"degraded"` status if running in memory when MongoDB is optional.

5. **Crash-Resilient Job Scheduling**
   - Configurable `JOB_BACKEND`: supports `"inprocess"` (FastAPI `BackgroundTasks` for lightweight local runs) and `"rq"` (Redis Queue for production distributed worker fleets).
   - Stale job recovery on startup: any jobs left in `pending` or `processing` states by a terminated server process are automatically marked failed or requeued.

6. **Security & Cost Guards**
   - **API-Key Authentication**: Protected endpoints require `X-API-Key` matching `ALMA_API_KEYS` (disabled with explicit console warnings only when `ALMA_AUTH_DISABLED=true`).
   - **Token Rate Limiting**: Enforces a per-key rate limit (default 10 req/hour) on generation and curriculum extraction endpoints, returning `429 Too Many Requests`.
   - **Payload & File Guards**: Enforces `MAX_UPLOAD_MB` (413 response) and verifies `%PDF` magic bytes on curriculum uploads.
   - **CORS Protection**: Origin-checked via `ALLOWED_ORIGINS` (disallowing wildcard `*` with credentials).

---

## 🚀 Run Modes

The repository supports three distinct execution modes:

### Mode 1: FastAPI REST API
Runs the production HTTP REST API powering curriculum management, generation jobs, and student runtime telemetry:
```bash
uvicorn alma_lessons.main:app --app-dir src --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger documentation is available at `http://localhost:8000/docs`.

### Mode 2: Distributed Background Worker
When `JOB_BACKEND=rq`, workers poll Redis to process generation jobs independently of the API web servers:
```bash
python -m alma_lessons.worker
```

### Mode 3: Streamlit Workbench
Interactive teacher inspection and editing workbench:
```bash
streamlit run app.py
```
Open `http://localhost:8501` to preview, edit, approve, or regenerate lessons.

---

## 🐳 Docker Compose Quickstart

The entire ecosystem (FastAPI, RQ Worker, MongoDB, Redis) can be launched with Docker Compose:

```bash
# 1. Start core API, RQ Worker, MongoDB, and Redis
docker compose up --build

# 2. Launch with Streamlit Workbench UI included
docker compose --profile ui up --build

# 3. Run End-to-End Smoke Test inside Docker
docker compose --profile test run --rm smoke-test
```

---

## 🔐 Authentication & API Usage

All API endpoints except `/api/v1/health` require an API key passed in the request header:

```bash
curl -X GET "http://localhost:8000/api/v1/lessons" \
     -H "X-API-Key: alma-dev-secret-key-12345"
```

- Missing or invalid key: `401 Unauthorized`
- Token rate limit exceeded: `429 Too Many Requests`
- File upload too large: `413 Request Entity Too Large`

For local offline development and test automation, set `ALMA_AUTH_DISABLED=true` in your `.env` file.

---

## ⚙️ Environment Variables

Configure application settings by copying `.env.example` to `.env`:

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | `""` | Google Gemini API key |
| `GROQ_API_KEY` | `""` | Groq API key |
| `OPENROUTER_API_KEY` | `""` | OpenRouter backup API key |
| `DEFAULT_GENERATOR_MODEL` | `gemini-3.5-flash-lite` | Default LLM model for outlines and sections |
| `DEFAULT_BRIDGE_MODEL` | `gemini-3.5-flash-lite` | Default LLM model for narrative bridge transitions |
| `DEFAULT_JUDGE_MODEL` | `gemini-3.5-flash-lite` | *Reserved:* Model for future quality judge |
| `DEFAULT_GEMINI_MODEL` | `gemini-3.5-flash-lite` | Fallback Gemini model |
| `DEFAULT_GROQ_MODEL` | `llama-3.3-70b-versatile` | Fallback Groq model |
| `DEFAULT_OPENROUTER_MODEL`| `google/gemini-2.5-flash` | Fallback OpenRouter model |
| `DEFAULT_WORDS_PER_MINUTE` | `140` | Speech rate for narration timing calculations |
| `USE_MONGODB` | `true` | Enable MongoDB integration |
| `REQUIRE_MONGODB` | `false` | Fail fast at startup if MongoDB is unreachable (`true` in Docker) |
| `MONGODB_URI` | `mongodb://127.0.0.1:27017` | MongoDB connection connection string |
| `MONGODB_DB_NAME` | `alma_lessons` | MongoDB database name |
| `JOB_BACKEND` | `inprocess` | Queue backend: `inprocess` (BackgroundTasks) or `rq` (Redis Queue) |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Redis connection URL for RQ jobs |
| `ALMA_API_KEYS` | `alma-dev-secret-key-12345` | Comma-separated list of authorized API keys |
| `ALMA_AUTH_DISABLED` | `false` | Set `true` to disable auth for local development/testing |
| `ALLOWED_ORIGINS` | `http://localhost:3000,...` | Comma-separated CORS allowed origins |
| `MAX_UPLOAD_MB` | `10` | Maximum PDF file upload size in megabytes |
| `RATE_LIMIT_PER_HOUR` | `10` | Max generation and extraction calls per key/IP per hour |
| `MAX_ACTIVE_GENERATIONS` | `5` | Maximum concurrent active generation jobs |
| `ALMA_SEED_DEMO_DATA` | `false` | Seed mock student demo record (`student_mohamad_001`) |

---

## 🧪 Testing and Evaluations

### Run Unit and Integration Tests
Zero external dependencies and zero real LLM spend. All tests use isolated in-memory storage and `FakeLLMClient`:
```bash
# Set USE_MONGODB=false and run pytest
$env:USE_MONGODB="false"; python -m pytest tests -q
```

### Run Ruff Code Quality Linter
```bash
python -m ruff check src tests scripts
```

### Run Token-Free Evaluation Harness
Evaluates curriculum specifications across multiple languages (Python, JavaScript, C++, Java, Scratch) and grade levels (5-10), including Arabic specifications and scope constraint notes:
```bash
# Token-free run with deterministic fake model
python scripts/run_evals.py

# Run on first 3 specs
python scripts/run_evals.py --limit 3

# Compare regression against previous results
python scripts/run_evals.py --limit 3 --compare evals/results/previous_run.json
```

> [!NOTE]
> Running evals against live models requires both `--provider <name>` and `--confirm-spend` to prevent accidental token consumption:
> ```bash
> python scripts/run_evals.py --provider gemini --confirm-spend --limit 2
> ```

### Run End-to-End Smoke Test
Validates MongoDB schema persistence, student runtime progression, and job polling:
```bash
python scripts/e2e_smoke_test.py
```
*(Automatically skipped with an informative message if MongoDB is not reachable).*

---

## 📂 Project Structure

```
ALMA-AI/
├── .github/workflows/         # GitHub Actions CI workflow
│   └── ci.yml
├── docker-compose.yml         # Compose stack: api, worker, mongo, redis, workbench
├── Dockerfile                 # Slim non-root production API/worker container
├── Dockerfile.ui              # Streamlit container
├── requirements.txt           # Production API dependencies (pinned ==)
├── requirements-dev.txt       # Pytest, ruff, development tools
├── requirements-ui.txt        # Streamlit UI dependencies
├── pyproject.toml             # Project metadata, pytest & ruff configs
├── app.py                     # Streamlit teacher workbench
├── evals/                     # Evaluation harness
│   ├── specs/                 # 16 LessonSpec test files (Python, JS, C++, Java, Arabic, Scope Notes)
│   └── results/               # Timestamped evaluation JSON and Markdown reports
├── prompts/v1/                # Versioned prompt templates
│   ├── system.md
│   ├── outline.md
│   ├── section.md
│   ├── bridge.md
│   ├── intro_conclusion.md
│   ├── lesson_practice.md
│   ├── segment_assessment.md
│   └── judge_quality.md
├── scripts/
│   ├── run_evals.py           # Evaluation pipeline harness & regression comparison
│   └── e2e_smoke_test.py      # End-to-end integration verification script
├── src/alma_lessons/
│   ├── api/                   # FastAPI application layer
│   │   ├── routers/           # /lessons, /jobs, /runtime, /curriculum, /health
│   │   ├── deps.py            # Client dependency injection
│   │   ├── schemas.py         # Request and response models
│   │   ├── security.py        # API-Key authentication, rate limiting, and size guards
│   │   └── client.py          # HTTP client helper
│   ├── curriculum/            # PDF text and curriculum extraction (PyMuPDF)
│   │   └── extractor.py
│   ├── domain/                # Pydantic core domain models
│   │   ├── spec.py            # LessonSpec & curriculum constraints
│   │   ├── content.py         # LessonContent, Section, Block
│   │   ├── assessment.py      # DiagnosticQuestion, Puzzles, CodingExercise
│   │   ├── segment.py         # Narration Segment & LessonSegmentation
│   │   └── state.py           # Lifecycle state machine & transition rules
│   ├── generation/            # Multi-pass generation pipeline
│   │   ├── pipeline.py        # LessonGenerationPipeline orchestrator
│   │   ├── prompts.py         # Prompt template loader
│   │   └── tasks.py           # Background generation tasks & stale job recovery
│   ├── llm/                   # Multi-provider client abstraction with structured telemetry
│   │   ├── interface.py       # BaseLLMClient & LLMResponse
│   │   ├── google_client.py   # Gemini REST client adapter
│   │   ├── groq_client.py     # Groq SDK client adapter
│   │   ├── openrouter_client.py # OpenRouter client adapter
│   │   └── fake_client.py     # Offline deterministic mock client
│   ├── segmentation/          # Audio narration chunker (105-140 words/segment)
│   │   └── segmenter.py
│   ├── storage/               # Dual persistence layer
│   │   ├── mongo_lesson_store.py      # MongoDB lesson store (Mongoose schema aligned)
│   │   ├── memory_store.py            # In-memory lesson store
│   │   ├── mongo_student_repository.py# MongoDB student profile telemetry repository
│   │   ├── student_repository.py      # In-memory student repository
│   │   ├── session_repository.py      # Student lesson sessions repository
│   │   └── job_manager.py             # Asynchronous generation job manager
│   ├── validation/            # Quality & integrity validation
│   │   ├── schema_validator.py        # Structural & type validation
│   │   ├── structure_validator.py     # Objective coverage & placeholder checks
│   │   ├── llm_judge.py               # (Planned) Independent LLM quality judge
│   │   └── runner.py                  # ValidationRunner aggregator
│   ├── config.py              # Central Pydantic application settings
│   ├── main.py                # FastAPI app initialization, CORS, and lifespan handlers
│   └── worker.py              # RQ worker entrypoint & CLI
└── tests/                     # Automated test suite
    ├── test_api.py            # API endpoints, security, auth, and runtime tests
    ├── test_curriculum.py     # PDF curriculum extraction tests
    ├── test_domain.py         # Domain models and transition validation
    ├── test_evals.py          # Truncated JSON, Arabic spec, and scope notes tests
    ├── test_generation.py     # Pipeline generation tests
    ├── test_llm_clients.py    # LLM client adapters tests
    ├── test_segmentation.py   # Narration segmentation tests
    ├── test_storage.py        # Storage and versioning tests
    └── test_validation.py     # Schema and structure validation tests
```

---

## 🔮 Planned & Roadmap

- **LLM Quality Judge**: The codebase contains an independent multi-metric pedagogical evaluator (`src/alma_lessons/validation/llm_judge.py`) designed to evaluate student cognitive load, age-appropriateness, and code correctness using an independent model family. To minimize token expenditure, this component is intentionally deferred and will be wired into the generation workflow behind an opt-in release flag.
- **TTS Audio Synthesis**: Future integration of automated text-to-speech rendering leveraging the segmented narration metadata and timing constraints generated by `BasicLessonSegmenter`.
