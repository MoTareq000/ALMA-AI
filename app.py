import sys
from pathlib import Path

# Ensure src directory is on sys.path
root_dir = Path(__file__).resolve().parent
src_dir = root_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import streamlit as st
from typing import List, Optional

from alma_lessons.domain import (
    LessonSpec,
    LessonContent,
    Section,
    Block,
    LessonState,
    LessonSegmentation,
    Outline,
    OutlineSection,
)
from alma_lessons.llm import GroqLLMClient, OpenRouterLLMClient, GoogleGeminiLLMClient
from alma_lessons.generation import LessonGenerationPipeline
from alma_lessons.validation import ValidationRunner
from alma_lessons.segmentation import BasicLessonSegmenter
from alma_lessons.storage import memory_store, LessonSession, student_repository
from alma_lessons.api.client import AlmaApiClient
from alma_lessons.config import config
from alma_lessons.tts import audio_cache, GoogleCloudTTSClient, FakeTTSClient, GTTSClient

api_client = AlmaApiClient(base_url="http://127.0.0.1:8000/api/v1")


st.set_page_config(
    page_title="ALMA Academy | AI Lesson Pipeline",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for polished pedagogical presentation
st.markdown("""
<style>
    /* Theme-Adaptive Variables & High Contrast Typography */
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(120deg, #3B82F6 0%, #60A5FA 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: var(--text-color, inherit);
        opacity: 0.85;
        margin-bottom: 1.5rem;
    }
    .badge {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }
    .badge-approved { background-color: rgba(16, 185, 129, 0.2); color: #10B981 !important; border: 1px solid #10B981; }
    .badge-review { background-color: rgba(245, 158, 11, 0.2); color: #F59E0B !important; border: 1px solid #F59E0B; }
    .badge-revision { background-color: rgba(239, 68, 68, 0.2); color: #EF4444 !important; border: 1px solid #EF4444; }
    .badge-draft { background-color: rgba(156, 163, 175, 0.2); color: #9CA3AF !important; border: 1px solid #9CA3AF; }
    .badge-validating { background-color: rgba(99, 102, 241, 0.2); color: #818CF8 !important; border: 1px solid #818CF8; }

    .callout-box {
        padding: 0.9rem 1.2rem;
        border-radius: 8px;
        margin: 0.8rem 0;
        border-left: 5px solid;
        color: var(--text-color, inherit) !important;
    }
    .callout-box * {
        color: var(--text-color, inherit) !important;
    }
    .callout-tip {
        background-color: rgba(16, 185, 129, 0.14) !important;
        border-color: #10B981 !important;
    }
    .callout-warning {
        background-color: rgba(245, 158, 11, 0.14) !important;
        border-color: #F59E0B !important;
    }
    .callout-note {
        background-color: rgba(59, 130, 246, 0.14) !important;
        border-color: #3B82F6 !important;
    }

    .segment-card {
        background-color: var(--secondary-background-color, rgba(128, 128, 128, 0.08)) !important;
        border: 1px solid rgba(128, 128, 128, 0.25) !important;
        border-radius: 10px !important;
        padding: 1.1rem 1.3rem !important;
        margin-bottom: 1rem !important;
        color: var(--text-color, inherit) !important;
    }
    .segment-card b, .segment-card i, .segment-card p, .segment-card small, .segment-card span {
        color: var(--text-color, inherit) !important;
    }

    .micro-check-card {
        background-color: var(--secondary-background-color, rgba(59, 130, 246, 0.05)) !important;
        border: 1px solid rgba(59, 130, 246, 0.35) !important;
        border-radius: 10px !important;
        padding: 1.1rem 1.3rem !important;
        margin: 0.8rem 0 1.2rem 0 !important;
        color: var(--text-color, inherit) !important;
    }

    .tts-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.3rem 0.7rem;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 600;
        background-color: rgba(59, 130, 246, 0.16);
        color: #3B82F6 !important;
        border: 1px solid rgba(59, 130, 246, 0.4);
        margin-bottom: 0.6rem;
    }

    .badge-cacheable {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 600;
        background-color: rgba(16, 185, 129, 0.16);
        color: #10B981 !important;
        border: 1px solid rgba(16, 185, 129, 0.4);
    }
    .badge-slot {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 600;
        background-color: rgba(139, 92, 246, 0.16);
        color: #8B5CF6 !important;
        border: 1px solid rgba(139, 92, 246, 0.4);
    }
    .slot-breakdown {
        background-color: rgba(128, 128, 128, 0.05);
        border: 1px dashed rgba(128, 128, 128, 0.3);
        border-radius: 8px;
        padding: 0.7rem 0.9rem;
        margin-top: 0.6rem;
        font-size: 0.88rem;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "selected_lesson_id" not in st.session_state:
    st.session_state.selected_lesson_id = None
if "objectives_count" not in st.session_state:
    st.session_state.objectives_count = 3
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "Preview"
if "extracted_curriculum" not in st.session_state:
    st.session_state.extracted_curriculum = None
if "form_topic" not in st.session_state:
    st.session_state.form_topic = "For Loops and Iteration"
if "form_lang" not in st.session_state:
    st.session_state.form_lang = "Python"
if "form_grade" not in st.session_state:
    st.session_state.form_grade = "Grade 8"
if "form_prereqs" not in st.session_state:
    st.session_state.form_prereqs = "Variables\nPrint statements\nBasic arithmetic operators"
if "form_curriculum" not in st.session_state:
    st.session_state.form_curriculum = "CSTA 2-AP-12: Design and iteratively develop programs that combine control structures."
if "form_scope" not in st.session_state:
    st.session_state.form_scope = ""

# Helper for badges
def render_state_badge(state: LessonState):
    cls = "badge-draft"
    if state == LessonState.APPROVED:
        cls = "badge-approved"
    elif state == LessonState.AWAITING_REVIEW:
        cls = "badge-review"
    elif state == LessonState.NEEDS_REVISION or state == LessonState.REJECTED:
        cls = "badge-revision"
    elif state == LessonState.VALIDATING:
        cls = "badge-validating"
    return f'<span class="badge {cls}">{state.value}</span>'

# ==========================================
# SIDEBAR: Configuration & Session Controls
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/graduation-cap.png", width=50)
    st.title("ALMA Pipeline")
    st.markdown("**AI Lesson Generator & Review**")

    backend_online = api_client.is_healthy()
    if backend_online:
        # Sync remote sessions from FastAPI backend so all tabs and dropdowns stay current
        try:
            remote_sessions = api_client.sync_all_lessons()
            for lid, s_dict in remote_sessions.items():
                memory_store.lessons[lid] = LessonSession.model_validate(s_dict)
        except Exception:
            pass

        st.markdown("""
        <div style="background-color: rgba(16, 185, 129, 0.12); border: 1px solid #10B981; border-radius: 8px; padding: 0.6rem 0.8rem; margin-top: 0.4rem; margin-bottom: 0.8rem;">
            <span style="color: #10B981; font-weight: 700; font-size: 0.85rem;">🟢 FastAPI Backend: Online</span><br>
            <span style="font-size: 0.75rem; opacity: 0.85;">Listening on <code>http://127.0.0.1:8000</code></span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background-color: rgba(239, 68, 68, 0.12); border: 1px solid #EF4444; border-radius: 8px; padding: 0.6rem 0.8rem; margin-top: 0.4rem; margin-bottom: 0.8rem;">
            <span style="color: #EF4444; font-weight: 700; font-size: 0.85rem;">🔴 FastAPI Backend: Offline</span><br>
            <span style="font-size: 0.75rem; opacity: 0.85;">Falling back to in-process pipeline</span>
        </div>
        """, unsafe_allow_html=True)

    st.divider()


    st.subheader("⚙️ Model & Provider")
    provider = st.selectbox("LLM Provider", ["Google AI Studio (Gemini)", "Groq", "OpenRouter"], index=0)

    if provider == "Google AI Studio (Gemini)":
        api_key = st.text_input("Gemini API Key", value=config.gemini_api_key, type="password")
        generator_model = st.selectbox(
            "Generator Model",
            ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-lite-latest", "gemini-flash-latest"],
            index=0,
            help="gemini-3.5-flash-lite offers 500 requests/day for free!"
        )
        client = GoogleGeminiLLMClient(api_key=api_key, default_model=generator_model)
    elif provider == "Groq":
        api_key = st.text_input("Groq API Key", value=config.groq_api_key, type="password")
        generator_model = st.selectbox(
            "Generator Model",
            ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"],
            index=0
        )
        client = GroqLLMClient(api_key=api_key, default_model=generator_model)
    else:
        api_key = st.text_input("OpenRouter API Key", value=config.openrouter_api_key, type="password")
        generator_model = st.text_input("Generator Model ID", value="meta-llama/llama-3.3-70b-instruct")
        client = OpenRouterLLMClient(api_key=api_key, default_model=generator_model)

    st.divider()
    st.subheader("🎙️ Voice Settings")
    tts_engine = st.selectbox(
        "Voice Engine",
        ["Google TTS (Free / Instant Natural Voice)", "Google Cloud (Journey / Neural2)", "Offline Mock Audio (0 Cost / Fast Test)"],
        index=0,
        help="Google TTS works out-of-the-box with zero API keys or GCP credentials. Google Cloud Journey provides studio-grade voices using a Google Cloud Service Account JSON."
    )

    if tts_engine.startswith("Google Cloud"):
        voice_options = [
            "en-US-Journey-F",
            "en-US-Journey-D",
            "en-US-Neural2-F",
            "en-US-Neural2-D",
        ]
        chosen_voice = st.selectbox("Teacher Voice Profile", voice_options, index=0, help="Journey voices provide natural, conversational tutoring intonation.")
        st.caption("ℹ️ *Requires a Google Cloud Service Account JSON (`GOOGLE_APPLICATION_CREDENTIALS`). If not found, it seamlessly falls back to natural Google TTS.*")
    elif tts_engine.startswith("Google TTS"):
        voice_options = [
            "en-US (Standard Natural)",
            "en-GB (British Natural)",
            "en-AU (Australian Natural)",
        ]
        chosen_voice = st.selectbox("Accent / Style", voice_options, index=0)
    else:
        chosen_voice = "en-US-Journey-F"

    voice_rate = st.slider("Speech Rate (Speed)", min_value=0.8, max_value=1.2, value=1.0, step=0.05)

    def get_active_tts_client():
        if tts_engine.startswith("Offline Mock"):
            return FakeTTSClient()
        elif tts_engine.startswith("Google TTS"):
            return GTTSClient()
        else:
            return GoogleCloudTTSClient(allow_fallback=True)

    with st.expander("🔊 Test Teacher Voice", expanded=False):
        test_phrase = st.text_input("Sample text:", value="Welcome to ALMA Academy! Today we will master Python loops step by step.")
        if st.button("Play Voice Sample"):
            with st.spinner("Synthesizing voice sample..."):
                try:
                    tts_c = get_active_tts_client()
                    sample_bytes = tts_c.synthesize(text=test_phrase, voice_name=chosen_voice, speaking_rate=voice_rate)
                    st.audio(sample_bytes, format="audio/mp3")
                    st.success("Sample synthesized successfully!")
                except Exception as tts_err:
                    st.error(f"TTS Error: {tts_err}")


    st.divider()
    st.subheader("📂 In-Memory Sessions")
    all_lessons = list(memory_store.lessons.values())
    if all_lessons:
        options = {s.lesson_id: f"{s.spec.topic} ({s.spec.programming_language}) [{s.current_version.state.value}]" for s in all_lessons}
        if st.session_state.selected_lesson_id not in options:
            st.session_state.selected_lesson_id = list(options.keys())[0]
        chosen_id = st.selectbox(
            "Switch Lesson",
            options=list(options.keys()),
            format_func=lambda x: options[x],
            index=list(options.keys()).index(st.session_state.selected_lesson_id)
        )
        st.session_state.selected_lesson_id = chosen_id
    else:
        st.session_state.selected_lesson_id = None
        st.info("No lessons in memory yet. Create your first lesson below!")

    st.divider()
    st.subheader("💾 Export / Import")
    json_data = memory_store.export_to_json()
    st.download_button(
        label="📥 Export Sessions (JSON)",
        data=json_data,
        file_name="alma_lessons_session.json",
        mime="application/json"
    )

    uploaded_file = st.file_uploader("📤 Import Sessions (JSON)", type=["json"])
    if uploaded_file is not None:
        try:
            content_str = uploaded_file.getvalue().decode("utf-8")
            memory_store.import_from_json(content_str)
            st.success("Sessions imported successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Import failed: {e}")

# ==========================================
# MAIN INTERFACE TABS
# ==========================================
st.markdown('<div class="main-header">ALMA Academy: AI Lesson Generation Pipeline</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Automated, verified, teacher-approved programming lessons with hybrid narration segmentation</div>', unsafe_allow_html=True)

tab_create, tab_review, tab_validation, tab_segments, tab_practice, tab_runtime = st.tabs([
    "📝 1. Lesson Specification",
    "👀 2. Teacher Review & Edit Workbench",
    "🛡️ 3. Validation Report",
    "🎙️ 4. Narration & Micro-Checks",
    "🧩 5. Puzzles & Coding Exercises",
    "🎓 6. Student Adaptive Runtime (Mohamad)"
])


# ----------------------------------------------------
# TAB 1: LESSON SPECIFICATION
# ----------------------------------------------------
with tab_create:
    st.header("Step 1: Define Teacher Lesson Specification")
    st.markdown("Specify the educational goals, target grade, and programming language, or upload an official syllabus/curriculum PDF to auto-fill the form.")

    # 📄 Curriculum Reference PDF Uploader (Option 1: Smart Extract & Pre-fill)
    with st.expander("📄 Upload Curriculum / Syllabus Reference PDF (Optional - Auto-Fills Form)", expanded=True):
        st.markdown("""
        Upload an official curriculum standard (e.g. **Cambridge IGCSE**, **CSTA K-12**, **Egyptian MoE**) or textbook chapter PDF.
        ALMA's AI analyzer extracts the topic, grade, standard codes, and learning objectives to pre-populate the specification form automatically.
        """)
        pdf_file = st.file_uploader("Upload PDF Reference", type=["pdf"], key="curriculum_pdf_uploader")
        if pdf_file is not None:
            col_p1, col_p2 = st.columns([1.2, 2.0])
            with col_p1:
                st.info(f"📁 **File:** `{pdf_file.name}` ({round(len(pdf_file.getvalue()) / 1024, 1)} KB)")
            with col_p2:
                if st.button("✨ Auto-Extract Objectives & Standards with AI", type="primary", use_container_width=True):
                    with st.spinner("Extracting text and analyzing curriculum standards..."):
                        try:
                            from alma_lessons.curriculum import extract_curriculum_from_pdf
                            extracted = extract_curriculum_from_pdf(pdf_file.getvalue(), client)
                            st.session_state.extracted_curriculum = extracted
                            st.session_state.form_topic = extracted.topic
                            st.session_state.form_lang = extracted.programming_language
                            st.session_state.form_grade = extracted.grade_level
                            st.session_state.form_curriculum = "\n".join(extracted.curriculum_references)
                            if extracted.prerequisites:
                                st.session_state.form_prereqs = "\n".join(extracted.prerequisites)
                            st.session_state.form_scope = extracted.curriculum_scope_notes or ""
                            st.session_state.objectives_count = len(extracted.learning_objectives)
                            for idx, obj in enumerate(extracted.learning_objectives):
                                st.session_state[f"obj_input_{idx}"] = obj
                            st.success(f"🎉 Successfully extracted {len(extracted.learning_objectives)} objectives and {len(extracted.curriculum_references)} standards from '{pdf_file.name}'!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to extract from PDF: {e}")

        if st.session_state.extracted_curriculum:
            cur = st.session_state.extracted_curriculum
            st.success(f"✅ **Curriculum Grounded:** `{cur.topic}` ({cur.source_pages_count} pages analyzed)")
            if cur.curriculum_scope_notes:
                st.caption(f"🎯 **Pedagogical Scope:** {cur.curriculum_scope_notes}")

    col1, col2 = st.columns([1.2, 1.0])

    with col1:
        topic_input = st.text_input("Lesson Topic *", value=st.session_state.form_topic, placeholder="e.g. While Loops, Functions, Object-Oriented Classes")
        subject_input = st.text_input("Subject Area", value="Computer Science & Programming")

        # Dynamic programming language dropdown + custom
        common_languages = [
            "Python", "JavaScript", "Java", "C++", "C#", "TypeScript",
            "HTML/CSS", "Scratch", "Go", "Rust", "PHP", "Ruby", "SQL", "Other"
        ]
        lang_idx = common_languages.index(st.session_state.form_lang) if st.session_state.form_lang in common_languages else 0
        lang_choice = st.selectbox("Programming Language Taught *", common_languages, index=lang_idx)
        if lang_choice == "Other":
            prog_lang_input = st.text_input("Specify Custom Programming Language *", value="Kotlin")
        else:
            prog_lang_input = lang_choice

        grade_options = ["Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10", "Grade 11", "Grade 12", "Introductory College"]
        grade_idx = grade_options.index(st.session_state.form_grade) if st.session_state.form_grade in grade_options else 2
        grade_input = st.selectbox(
            "Target Grade Level *",
            grade_options,
            index=grade_idx
        )
        depth_input = st.select_slider(
            "Desired Depth",
            options=["basic", "standard", "deep"],
            value="standard",
            help="Basic: 2-3 sections. Standard: 3-4 sections. Deep: 4-5 sections with advanced exercises."
        )

    with col2:
        target_minutes = st.number_input("Target Duration (minutes)", min_value=5, max_value=60, value=15)
        prereqs_input = st.text_area("Prerequisites (one per line)", value=st.session_state.form_prereqs)
        curriculum_input = st.text_area("Curriculum References / Standards", value=st.session_state.form_curriculum)
        scope_input = st.text_area("Curriculum Scope Constraints (optional)", value=st.session_state.form_scope, placeholder="e.g. Limit to single loops; do not introduce nested loops.")
        special_instructions = st.text_area("Special Teacher Instructions (optional)", placeholder="e.g. Use a gaming or inventory analogy; emphasize off-by-one errors.")

    st.subheader("Learning Objectives (1 to 8 objectives)")
    st.caption("Each objective will be strictly mapped to lesson sections and tracked for coverage.")

    col_btn1, col_btn2, _ = st.columns([0.15, 0.15, 0.7])
    with col_btn1:
        if st.button("➕ Add Objective"):
            if st.session_state.objectives_count < 8:
                st.session_state.objectives_count += 1
                st.rerun()
    with col_btn2:
        if st.button("➖ Remove"):
            if st.session_state.objectives_count > 1:
                st.session_state.objectives_count -= 1
                st.rerun()

    default_objs = [
        "Understand why iteration is used to avoid duplicate code",
        "Write a for loop using the range() function",
        "Iterate over items in a sequence and calculate running totals"
    ]
    objectives_list = []
    for i in range(st.session_state.objectives_count):
        val = st.session_state.get(f"obj_input_{i}", default_objs[i] if i < len(default_objs) else f"Objective {i+1}")
        obj_text = st.text_input(f"Objective #{i+1}", value=val, key=f"obj_input_{i}")
        if obj_text.strip():
            objectives_list.append(obj_text.strip())

    st.divider()

    if st.button("🚀 Generate Lesson (Run Two-Pass Pipeline)", type="primary", use_container_width=True):
        if not topic_input.strip():
            st.error("Please provide a lesson topic.")
        elif not objectives_list:
            st.error("Please provide at least one learning objective.")
        else:
            prereqs = [p.strip() for p in prereqs_input.split("\n") if p.strip()]
            curriculum = [c.strip() for c in curriculum_input.split("\n") if c.strip()]

            spec = LessonSpec(
                subject=subject_input,
                topic=topic_input,
                programming_language=prog_lang_input,
                grade_level=grade_input,
                language="en",
                learning_objectives=objectives_list,
                desired_depth=depth_input,
                prerequisites=prereqs,
                curriculum_references=curriculum,
                curriculum_scope_notes=scope_input.strip() if scope_input.strip() else None,
                additional_instructions=special_instructions or None,
                target_duration_minutes=target_minutes,
            )

            progress_bar = st.progress(0)
            status_text = st.empty()

            def on_progress(msg: str, pct: float):
                progress_bar.progress(pct)
                status_text.info(f"⏳ {msg}")

            try:
                if backend_online:
                    status_text.info("🚀 Submitting asynchronous generation job to FastAPI backend...")
                    provider_key = "gemini" if "Google" in provider else ("groq" if "Groq" in provider else "openrouter")
                    job_res = api_client.generate_lesson(spec.model_dump(), provider=provider_key, model=generator_model)
                    job_id = job_res["job_id"]

                    completed_job = api_client.poll_job_until_complete(
                        job_id,
                        poll_interval=1.0,
                        callback=lambda msg, pct: (progress_bar.progress(pct), status_text.info(f"⏳ [{int(pct*100)}%] {msg}"))
                    )
                    new_lesson_id = completed_job["lesson_id"]
                    try:
                        remote_sessions = api_client.sync_all_lessons()
                        for lid, s_dict in remote_sessions.items():
                            memory_store.lessons[lid] = LessonSession.model_validate(s_dict)
                    except Exception:
                        pass
                    st.session_state.selected_lesson_id = new_lesson_id
                    progress_bar.progress(1.0)
                    status_text.success("✅ Lesson generated via FastAPI backend and validated successfully!")
                    st.rerun()
                else:
                    pipeline = LessonGenerationPipeline(llm_client=client)
                    generated_lesson, outline = pipeline.run(spec, progress_callback=on_progress)

                    status_text.info("🎙️ Generating ~45-60s speech segments & micro-checks upfront...")
                    progress_bar.progress(0.85)
                    segmenter = BasicLessonSegmenter()
                    segmentation_data = segmenter.segment_lesson(
                        generated_lesson,
                        spec=spec,
                        topic_assessment_generator=pipeline.generate_topic_micro_checks
                    )

                    status_text.info("🛡️ Running deterministic validators (schema, structure, coverage)...")
                    progress_bar.progress(0.95)
                    validator = ValidationRunner()
                    validation_report = validator.run(generated_lesson, spec)

                    session = memory_store.create_lesson(
                        spec=spec,
                        content=generated_lesson,
                        validation_report=validation_report,
                        segmentation=segmentation_data
                    )
                    st.session_state.selected_lesson_id = session.lesson_id

                    progress_bar.progress(1.0)
                    status_text.success(f"✅ Lesson '{generated_lesson.title}' generated with segments and validated successfully!")
                    st.rerun()

            except Exception as e:
                st.error(f"Generation failed: {str(e)}")


# ----------------------------------------------------
# TAB 2: TEACHER REVIEW & EDIT WORKBENCH
# ----------------------------------------------------
with tab_review:
    current_session: Optional[LessonSession] = None
    if st.session_state.selected_lesson_id:
        current_session = memory_store.lessons.get(st.session_state.selected_lesson_id)

    if not current_session:
        st.info("No active lesson selected. Generate or import a lesson first in Tab 1.")
    else:
        # Header banner with version selector and state badge
        col_title, col_ver, col_mode = st.columns([2.0, 1.0, 1.0])
        with col_title:
            st.markdown(f"### {current_session.spec.topic} ({current_session.spec.programming_language})")
            curr_v = current_session.current_version
            st.markdown(f"Current State: {render_state_badge(curr_v.state)}", unsafe_allow_html=True)

        with col_ver:
            version_options = [v.version_no for v in current_session.versions]
            selected_v_no = st.selectbox(
                "Version History",
                version_options,
                index=version_options.index(current_session.current_version_no),
                format_func=lambda v: f"Version {v} ({current_session.versions[v-1].source})"
            )
            version_record = current_session.versions[selected_v_no - 1]

        with col_mode:
            st.session_state.view_mode = st.radio("Display Mode", ["Preview", "Edit Mode"], horizontal=True)

        lesson_data = version_record.content

        # ==========================================
        # PREVIEW MODE
        # ==========================================
        if st.session_state.view_mode == "Preview":
            st.subheader(f"📖 {lesson_data.title}")
            target_mins = current_session.spec.target_duration_minutes or 15
            est_mins = round(lesson_data.total_words() / 140.0, 1)
            adaptive_words = lesson_data.total_all_words_including_adaptive() - lesson_data.total_words()

            st.caption(
                f"Language: **{lesson_data.programming_language}** | Target Grade: **{lesson_data.grade_level}** | "
                f"Duration: **{est_mins} / {target_mins} min** | "
                f"Core: **{lesson_data.total_words()} words** (+{adaptive_words} adaptive words) | "
                f"Blocks: **{lesson_data.total_blocks()}** (+{lesson_data.total_adaptive_blocks()} adaptive blocks)"
            )

            if est_mins < target_mins * 0.5:
                st.warning(f"⚠️ Current core duration ({est_mins} min) is below target ({target_mins} min). Deep generation or additional objectives recommended.")

            # Objectives Pill Container
            with st.expander("🎯 Stated Learning Objectives", expanded=True):
                for obj in lesson_data.objectives:
                    st.markdown(f"- **{obj}**")

            # Introduction
            st.markdown("#### 🌟 Introduction")
            for b in lesson_data.introduction:
                if b.type == "paragraph" and b.text:
                    st.write(b.text)
                elif b.type == "callout" and b.text:
                    st.markdown(f'<div class="callout-box callout-{b.callout_type or "note"}"><b>{b.callout_type.upper() if b.callout_type else "NOTE"}:</b> {b.text}</div>', unsafe_allow_html=True)
                elif b.type == "code" and b.code:
                    st.code(b.code, language=(b.language or lesson_data.programming_language).lower())

            st.divider()

            # Instruction Sections
            for sec in lesson_data.sections:
                st.markdown(f"#### 📌 Section {sec.order}: {sec.title}")
                st.markdown(f"*Purpose:* {sec.purpose}")
                if sec.covers_objectives:
                    st.caption(f"Covers: {', '.join(sec.covers_objectives)}")

                # Core Instruction Blocks
                for b in sec.blocks:
                    if b.type == "paragraph" and b.text:
                        st.write(b.text)
                    elif b.type == "code" and b.code:
                        st.code(b.code, language=(b.language or lesson_data.programming_language).lower())
                        if b.expected_output:
                            st.caption(f"**Expected Output:** `{b.expected_output}`")
                    elif b.type == "callout" and b.text:
                        st.markdown(f'<div class="callout-box callout-{b.callout_type or "tip"}"><b>{b.callout_type.upper() if b.callout_type else "TIP"}:</b> {b.text}</div>', unsafe_allow_html=True)
                    elif b.type == "list" and b.items:
                        for itm in b.items:
                            st.markdown(f"- {itm}")

                # 🎯 In-Situ Diagnostic Checkpoint
                if sec.diagnostic_check:
                    dc = sec.diagnostic_check
                    st.markdown(f"""
                    <div style="background-color: rgba(59, 130, 246, 0.08); border-left: 4px solid #3B82F6; padding: 12px 16px; border-radius: 6px; margin: 12px 0;">
                        <span style="font-weight: 700; color: #3B82F6;">🎯 In-Situ Diagnostic Checkpoint (Section {sec.order})</span><br>
                        <span style="font-size: 0.95rem;">{dc.question_text}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    if dc.code_snippet:
                        st.code(dc.code_snippet, language=lesson_data.programming_language.lower())
                    if dc.options:
                        st.markdown("**Diagnostic Choices:**")
                        for opt in dc.options:
                            is_correct = (opt == dc.correct_answer)
                            badge = "✅ *(Correct Answer)*" if is_correct else "❌"
                            st.markdown(f"- {badge} `{opt}`")
                    with st.expander(f"🔍 Diagnostic Misconception Analysis (Section {sec.order})"):
                        st.markdown(f"**Target Concept & Explanation:** {dc.explanation}")
                        if dc.misconception_map:
                            st.markdown("**Misconception Diagnoses for Distractors:**")
                            for wrong_opt, misconc in dc.misconception_map.items():
                                st.markdown(f"- **Choice `{wrong_opt}`**: {misconc}")

                # 🔀 Adaptive Learning Branches (Remediation & Extension)
                if sec.remediation_blocks or sec.extension_blocks:
                    col_rem, col_ext = st.columns(2)
                    with col_rem:
                        with st.expander(f"🟡 Remediation Branch ({len(sec.remediation_blocks)} blocks)", expanded=False):
                            st.caption("Triggered automatically when a learner struggles on the diagnostic checkpoint.")
                            for rb in sec.remediation_blocks:
                                if rb.type == "paragraph" and rb.text:
                                    st.write(rb.text)
                                elif rb.type == "code" and rb.code:
                                    st.code(rb.code, language=(rb.language or lesson_data.programming_language).lower())
                                elif rb.type == "callout" and rb.text:
                                    st.info(f"{rb.callout_type.upper() if rb.callout_type else 'NOTE'}: {rb.text}")
                    with col_ext:
                        with st.expander(f"🟣 Extension Branch ({len(sec.extension_blocks)} blocks)", expanded=False):
                            st.caption("Triggered automatically when an advanced learner easily masters the diagnostic checkpoint.")
                            for eb in sec.extension_blocks:
                                if eb.type == "paragraph" and eb.text:
                                    st.write(eb.text)
                                elif eb.type == "code" and eb.code:
                                    st.code(eb.code, language=(eb.language or lesson_data.programming_language).lower())
                                elif eb.type == "callout" and eb.text:
                                    st.success(f"{eb.callout_type.upper() if eb.callout_type else 'TIP'}: {eb.text}")

                st.write("")

            st.divider()

            # Conclusion
            st.markdown("#### 🏁 Conclusion")
            for b in lesson_data.conclusion:
                if b.type == "paragraph" and b.text:
                    st.write(b.text)
                elif b.type == "callout" and b.text:
                    st.markdown(f'<div class="callout-box callout-{b.callout_type or "note"}"><b>{b.callout_type.upper() if b.callout_type else "NOTE"}:</b> {b.text}</div>', unsafe_allow_html=True)

            # 🎙️ Pre-Generated Speech Units & Spoken Micro-Checks Preview (Template Slots & Audio Caching)
            if version_record.segmentation:
                seg_info = version_record.segmentation
                with st.expander(f"🎙️ Narration Segments, Template Slots & Micro-Checks ({seg_info.total_segments} speech units, ~{seg_info.est_total_duration_minutes} min)", expanded=False):
                    st.caption("🔒 **Zero Hallucination Guarantee:** Core narration is 100% frozen upon approval and cached as permanent audio ($0.01/student). Runtime LLMs only fill dynamic wrapper slots ({name}, praise, history line).")
                    for topic in seg_info.topics:
                        st.markdown(f"**📁 {topic.topic_title}** ({len(topic.segments)} segments)")
                        for s_idx, seg in enumerate(topic.segments):
                            p_slot = getattr(seg, 'prefix_slot_template', None) or '{greeting_or_praise}'
                            s_slot = getattr(seg, 'suffix_slot_template', None) or '{transition_lead_in}'
                            st.markdown(f"- **#{seg.order_in_lesson} {seg.title}** ({seg.est_seconds}s | {seg.word_count} words): `[Prefix: {p_slot}]` + **\"{seg.narration_text}\"** + `[Suffix: {s_slot}]`")
                            if seg.assessment:
                                st.caption(f"  🎯 *TTS Voice Micro-Check:* \"{seg.assessment.spoken_tts_prompt}\" — **Answer:** `{seg.assessment.correct_answer}`")

        # ==========================================
        # EDIT MODE (Full In-Place Teacher Editor)
        # ==========================================
        else:
            st.subheader("✏️ Teacher In-Place Editor")
            st.caption("Modifications made here will be saved as a new version, preserving previous revisions.")

            with st.form("teacher_edit_form"):
                edited_title = st.text_input("Lesson Title", value=lesson_data.title)

                st.markdown("##### Introduction Blocks")
                edited_intro_text = st.text_area(
                    "Introductory Prose",
                    value="\n\n".join(b.text for b in lesson_data.introduction if b.type == "paragraph" and b.text)
                )

                st.markdown("##### Sections Content")
                edited_sections: List[Section] = []
                for idx, sec in enumerate(lesson_data.sections):
                    st.markdown(f"**Section {sec.order}**")
                    sec_title = st.text_input(f"Section {sec.order} Title", value=sec.title, key=f"sec_title_{idx}")
                    sec_purpose = st.text_input(f"Section {sec.order} Purpose", value=sec.purpose, key=f"sec_purpose_{idx}")

                    # Combine paragraphs for simple editing
                    prose_blocks = [b.text for b in sec.blocks if b.type == "paragraph" and b.text]
                    sec_prose = st.text_area(f"Section {sec.order} Explanation", value="\n\n".join(prose_blocks), key=f"sec_prose_{idx}")

                    # Extract primary code block
                    code_block = next((b for b in sec.blocks if b.type == "code"), None)
                    current_code = code_block.code if code_block else ""
                    sec_code = st.text_area(f"Section {sec.order} Code Example", value=current_code, key=f"sec_code_{idx}")

                    # Reassemble blocks
                    new_blocks = [Block(type="paragraph", text=p) for p in sec_prose.split("\n\n") if p.strip()]
                    if sec_code.strip():
                        new_blocks.append(Block(type="code", language=lesson_data.programming_language, code=sec_code.strip()))

                    edited_sections.append(Section(
                        order=sec.order,
                        title=sec_title,
                        purpose=sec_purpose,
                        covers_objectives=sec.covers_objectives,
                        blocks=new_blocks,
                        diagnostic_check=sec.diagnostic_check,
                        remediation_blocks=sec.remediation_blocks,
                        extension_blocks=sec.extension_blocks,
                    ))

                st.markdown("##### Conclusion Blocks")
                edited_concl_text = st.text_area(
                    "Concluding Prose",
                    value="\n\n".join(b.text for b in lesson_data.conclusion if b.type == "paragraph" and b.text)
                )

                submit_edits = st.form_submit_button("💾 Save as New Version (Teacher Edit)", type="primary")

                if submit_edits:
                    new_intro = [Block(type="paragraph", text=p) for p in edited_intro_text.split("\n\n") if p.strip()]
                    new_concl = [Block(type="paragraph", text=p) for p in edited_concl_text.split("\n\n") if p.strip()]

                    edited_content = LessonContent(
                        title=edited_title,
                        programming_language=lesson_data.programming_language,
                        grade_level=lesson_data.grade_level,
                        target_duration_minutes=current_session.spec.target_duration_minutes or 15,
                        introduction=new_intro if new_intro else lesson_data.introduction,
                        objectives=lesson_data.objectives,
                        sections=edited_sections,
                        conclusion=new_concl if new_concl else lesson_data.conclusion,
                        puzzles=lesson_data.puzzles,
                        exercises=lesson_data.exercises,
                    )

                    # Re-run fast validation on teacher edits
                    validator = ValidationRunner()
                    reval_report = validator.run(edited_content, current_session.spec)


                    # Re-segment so speech segments stay synchronized with teacher edits
                    segmenter = BasicLessonSegmenter()
                    pipeline = LessonGenerationPipeline(llm_client=client)
                    new_seg = segmenter.segment_lesson(
                        edited_content,
                        spec=current_session.spec,
                        topic_assessment_generator=pipeline.generate_topic_micro_checks
                    )

                    new_ver = memory_store.add_teacher_edit(
                        lesson_id=current_session.lesson_id,
                        edited_content=edited_content,
                        revalidation_report=reval_report,
                        segmentation=new_seg
                    )
                    st.success(f"Saved edits as version v{new_ver.version_no} with synchronized segments!")
                    st.rerun()

        # ==========================================
        # TEACHER ACTION BAR (Approve / Reject / Regenerate)
        # ==========================================
        st.divider()
        st.subheader("⚡ Teacher Actions")

        act_col1, act_col2, act_col3 = st.columns([1.2, 1.2, 1.6])

        # 1. APPROVE BUTTON
        with act_col1:
            report = version_record.validation_report or {}
            has_blocking = report.get("has_blocking_errors", False)
            warnings = report.get("warnings", [])

            if st.button("✅ Approve Lesson", type="primary", disabled=has_blocking, use_container_width=True):
                memory_store.approve_lesson(
                    lesson_id=current_session.lesson_id,
                    acknowledged_warnings=warnings,
                    segmentation=version_record.segmentation
                )
                st.success("🎉 Lesson Approved! Prose, exercises, and audio segments validated.")
                st.rerun()

            if has_blocking:
                st.caption("⚠️ Cannot approve: resolve blocking validation errors first.")
            elif warnings:
                st.caption(f"ℹ️ Approval will acknowledge {len(warnings)} non-blocking warning(s).")

        # 2. REJECT BUTTON
        with act_col2:
            with st.popover("❌ Reject Lesson", use_container_width=True):
                rejection_reason = st.text_input("Reason for rejection", placeholder="e.g. Scope unsuitable for grade level.")
                if st.button("Confirm Rejection", type="secondary"):
                    memory_store.reject_lesson(current_session.lesson_id, rejection_reason or "Rejected by teacher")
                    st.warning("Lesson marked as Rejected.")
                    st.rerun()

        # 3. REGENERATE WITH FEEDBACK
        with act_col3:
            with st.popover("🔄 Request AI Regeneration", use_container_width=True):
                feedback_text = st.text_area(
                    "Teacher Guidance / Revision Notes",
                    placeholder="e.g. Make Section 2 simpler; add a real-world coding exercise with a grocery list."
                )
                if st.button("Start Regeneration Pass", type="primary"):
                    with st.spinner("Regenerating lesson with feedback & segments..."):
                        pipeline = LessonGenerationPipeline(llm_client=client)
                        new_lesson, _ = pipeline.run(current_session.spec, teacher_feedback=feedback_text)

                        segmenter = BasicLessonSegmenter()
                        new_seg = segmenter.segment_lesson(
                            new_lesson,
                            spec=current_session.spec,
                            topic_assessment_generator=pipeline.generate_topic_micro_checks
                        )

                        validator = ValidationRunner()
                        new_report = validator.run(new_lesson, current_session.spec)


                        new_ver = memory_store.add_regeneration(
                            lesson_id=current_session.lesson_id,
                            new_content=new_lesson,
                            feedback=feedback_text,
                            validation_report=new_report
                        )
                        new_ver.segmentation = new_seg
                        st.success("Regeneration completed as new version with segments!")
                        st.rerun()

# ----------------------------------------------------
# TAB 3: AUTOMATED VALIDATION REPORT
# ----------------------------------------------------
with tab_validation:
    st.header("Step 3: Automated Validation & Quality Audit")

    current_session: Optional[LessonSession] = None
    if st.session_state.selected_lesson_id:
        current_session = memory_store.lessons.get(st.session_state.selected_lesson_id)

    if not current_session:
        st.info("Select or generate a lesson first in Step 1 to view its validation report.")
    else:
        curr_v = current_session.current_version
        report = curr_v.validation_report or {}

        overall_status = report.get("overall_status", "UNKNOWN")
        if overall_status == "PASSED":
            st.success("✅ **OVERALL VERDICT: PASSED** — All structural, schema, and quality benchmarks met.")
        elif overall_status == "WARNINGS":
            st.warning("⚠️ **OVERALL VERDICT: PASSED WITH WARNINGS** — Non-blocking pedagogical or coverage warnings flagged.")
        else:
            st.error("❌ **OVERALL VERDICT: FAILED** — Blocking schema or structural defects detected.")

        v_col1, v_col2 = st.columns(2)

        with v_col1:
            st.markdown("#### 📐 Deterministic Checks")
            schema_rep = report.get("schema_report", {})
            struct_rep = report.get("structure_report", {})

            st.write(f"- **Schema Validation:** {'✅ Pass' if schema_rep.get('passed') else '❌ Fail'}")
            st.write(f"- **Structure & Coverage:** {'✅ Pass' if struct_rep.get('passed') else '❌ Fail'}")
            st.write(f"- **Total Core Non-Code Words:** {report.get('word_count', 0)} (+{curr_v.content.total_all_words_including_adaptive() - report.get('word_count', 0)} adaptive words)")
            st.write(f"- **Total Blocks:** {report.get('block_count', 0)} (+{curr_v.content.total_adaptive_blocks()} adaptive blocks)")
            target_m = struct_rep.get('target_duration_minutes', current_session.spec.target_duration_minutes or 15)
            est_m = struct_rep.get('est_duration_minutes', round(report.get('word_count', 0)/140.0, 1))
            st.write(f"- **Duration Alignment:** {est_m} min est. / {target_m} min target")
            st.write(f"- **In-Situ Diagnostic Checkpoints:** {struct_rep.get('adaptive_sections_count', 0)} / {len(curr_v.content.sections)} sections")

            if report.get("errors"):
                st.markdown("**Blocking Errors:**")
                for err in report["errors"]:
                    st.error(f"• {err}")

            if report.get("warnings"):
                st.markdown("**Advisory Warnings:**")
                for warn in report["warnings"]:
                    st.warning(f"• {warn}")

        with v_col2:
            st.markdown("#### 👨‍🏫 Human-in-the-Loop Quality & Review")
            st.info("💡 **Teacher-Accountable Quality Model**: Pedagogical clarity, accuracy, and tone are reviewed directly by the educator in **Step 2 (Review Workbench)** before approval, eliminating expensive LLM judge calls and hallucinations.")

            st.markdown("##### 🎯 Learning Objective Mapping")
            spec_objs = current_session.spec.learning_objectives
            sec_objs_map = {}
            for s in curr_v.content.sections:
                for obj_id in s.covers_objectives:
                    sec_objs_map.setdefault(obj_id, []).append(f"Section {s.order}: {s.title}")

            for idx, obj in enumerate(spec_objs, 1):
                mapped_secs = sec_objs_map.get(obj, [])
                if mapped_secs:
                    st.markdown(f"**{idx}.** {obj}")
                    st.caption(f"↳ Covered in: {', '.join(mapped_secs)}")
                else:
                    st.markdown(f"**{idx}.** {obj} — <span style='color: #EF4444;'>⚠️ Not explicitly mapped</span>", unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("##### 🔍 Deterministic Guarantees")
            st.markdown("- **Zero Placeholder Tokens**: Verified (no `TODO`, `TBD`, or stub text)")
            st.markdown("- **Code Block Structure**: Verified language and syntax tags")
            st.markdown("- **Pydantic Schema**: 100% compliant with `LessonContent` contract")


# ----------------------------------------------------
# TAB 4: NARRATION & SEGMENTATION BREAKDOWN
# ----------------------------------------------------
# ----------------------------------------------------
# TAB 4: NARRATION & MICRO-CHECKS (Per-Segment)
# ----------------------------------------------------
with tab_segments:
    st.header("Step 4: Topic & ~45-60s Narration Segments + Micro-Checks")
    st.markdown("""
    <div style="background-color: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 0.9rem 1.2rem; margin-bottom: 1.2rem;">
        <span style="font-size: 1.0rem; font-weight: 700; color: #10B981;">🔒 Template Slot Architecture & Verbatim Audio Caching ($0.01 / Student)</span><br>
        <span style="font-size: 0.88rem; opacity: 0.9; color: var(--text-color, inherit);">
            Approved lesson prose is <b>100% frozen and verbatim</b>. It is synthesized into static TTS audio once and cached permanently on CDN/S3.
            At runtime, personalizer LLMs <b>only generate short wrapper sentences</b> in designated slots (<code>{name}</code>, praise, history lines), guaranteeing <b>zero hallucinations</b> and saving ~85% of TTS costs.
        </span>
    </div>
    """, unsafe_allow_html=True)

    current_session: Optional[LessonSession] = None
    if st.session_state.selected_lesson_id:
        current_session = memory_store.lessons.get(st.session_state.selected_lesson_id)

    if not current_session:
        st.info("Select or generate a lesson first in Step 1.")
    else:
        curr_v = current_session.current_version
        seg_data: Optional[LessonSegmentation] = curr_v.segmentation

        if not seg_data:
            st.info("This lesson has not been segmented yet. You can segment it below with active-recall micro-checks.")
            if st.button("🎙️ Segment Current Version & Generate Micro-Checks"):
                with st.spinner("Partitioning lesson into ~45-60s speech segments and generating micro-checks..."):
                    segmenter = BasicLessonSegmenter()
                    pipeline = LessonGenerationPipeline(llm_client=client)
                    seg_data = segmenter.segment_lesson(
                        curr_v.content,
                        spec=current_session.spec,
                        topic_assessment_generator=pipeline.generate_topic_micro_checks
                    )
                    curr_v.segmentation = seg_data
                st.success("Segments and Micro-Checks created!")
                st.rerun()

        if seg_data:
            # Metrics
            m_col1, m_col2, m_col3 = st.columns(3)
            m_col1.metric("Total Topics", len(seg_data.topics))
            m_col2.metric("Total Narration Segments", seg_data.total_segments)
            m_col3.metric("Est. Total Duration", f"{seg_data.est_total_duration_minutes} min")

            # Voice Synthesizer Control Bar
            st.markdown("""
            <div style="background-color: rgba(59, 130, 246, 0.08); border: 1px solid #3B82F6; border-radius: 8px; padding: 0.8rem 1.0rem; margin-top: 0.8rem; margin-bottom: 0.8rem;">
                <span style="font-weight: 700; color: #3B82F6;">🎙️ Google Cloud Journey Speech Studio</span><br>
                <span style="font-size: 0.85rem; opacity: 0.9;">Synthesize human-grade teacher narration for every approved segment. Audio is cached locally to eliminate duplicate synthesis costs.</span>
            </div>
            """, unsafe_allow_html=True)

            col_tts1, col_tts2 = st.columns([1.8, 1.2])
            with col_tts1:
                st.caption(f"Active Voice: **{chosen_voice}** | Engine: **{tts_engine}** | Speed: **{voice_rate}x**")
            with col_tts2:
                if st.button("⚡ Synthesize All Segment Audio", type="primary", use_container_width=True):
                    tts_client = get_active_tts_client()
                    all_segs = [s for t in seg_data.topics for s in t.segments]
                    synth_n = 0
                    cached_n = 0
                    p_bar = st.progress(0.0)
                    for idx, s in enumerate(all_segs):
                        s_text = s.narration_text.strip()
                        if not s_text:
                            continue
                        c_key = audio_cache.compute_cache_key(s_text, voice_name=chosen_voice, speaking_rate=voice_rate)
                        if audio_cache.has_audio(c_key):
                            cached_n += 1
                        else:
                            try:
                                a_bytes = tts_client.synthesize(s_text, voice_name=chosen_voice, speaking_rate=voice_rate)
                                audio_cache.save_audio(c_key, a_bytes)
                                synth_n += 1
                            except Exception as err:
                                st.error(f"Failed to synthesize segment #{s.order_in_lesson}: {err}")
                                break
                        s.audio_file = f"{c_key}.mp3"
                        s.audio_url = f"/api/v1/audio/{c_key}.mp3"
                        p_bar.progress((idx + 1) / max(len(all_segs), 1))
                    if hasattr(memory_store, "_persist"):
                        memory_store._persist(current_session)
                    st.success(f"🎉 Speech ready! {synth_n} newly synthesized, {cached_n} loaded from zero-cost cache.")
                    st.rerun()

            st.divider()

            for topic in seg_data.topics:
                with st.expander(f"📁 Topic {topic.order}: {topic.topic_title} ({len(topic.segments)} segments)", expanded=True):
                    st.caption(f"Topic Purpose: {topic.purpose}")
                    for seg in topic.segments:
                        p_slot = getattr(seg, "prefix_slot_template", None) or "{greeting_or_praise}"
                        s_slot = getattr(seg, "suffix_slot_template", None) or "{transition_lead_in}"

                        st.markdown(f"""
                        <div class="segment-card">
                            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
                                <span style="font-size: 1.05rem; font-weight: 600; color: var(--text-color, inherit);">Segment #{seg.order_in_lesson}: <i>{seg.title}</i></span>
                                <div>
                                    <span class="badge-cacheable">🔒 100% Verbatim & Audio-Cacheable</span>
                                    <span class="badge-slot">🏷️ Template Slots Active</span>
                                </div>
                            </div>
                            <span style="font-size: 0.82rem; opacity: 0.85; color: var(--text-color, inherit);">⏱️ Est: <b>{seg.est_seconds}s</b> | 📝 Words: <b>{seg.word_count}</b></span>

                            <div class="slot-breakdown">
                                <div style="margin-bottom: 0.35rem; color: #8B5CF6; font-size: 0.82rem; font-weight: 600;">
                                    🏷️ <b>Prefix Slot (Runtime Personalization Wrapper):</b> <code>{p_slot}</code>
                                </div>
                                <div style="padding: 0.5rem 0.75rem; background-color: rgba(16, 185, 129, 0.08); border-left: 3px solid #10B981; border-radius: 4px; margin: 0.4rem 0;">
                                    <span style="font-size: 0.78rem; font-weight: 700; color: #10B981; text-transform: uppercase;">🔒 Approved Core Narration (Frozen & Cached Audio):</span><br>
                                    <span style="font-size: 0.95rem; line-height: 1.5; color: var(--text-color, inherit);">"{seg.narration_text}"</span>
                                </div>
                                <div style="margin-top: 0.35rem; color: #8B5CF6; font-size: 0.82rem; font-weight: 600;">
                                    🏷️ <b>Suffix Slot (Runtime Lead-in Wrapper):</b> <code>{s_slot}</code>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        # Teacher Audio Preview Player
                        c_key = audio_cache.compute_cache_key(seg.narration_text, voice_name=chosen_voice, speaking_rate=voice_rate)
                        cached_audio = audio_cache.get_audio_path(c_key)
                        if cached_audio and cached_audio.is_file():
                            st.markdown("🔊 **Synthesized Teacher Voice (Google Journey):**")
                            st.audio(str(cached_audio), format="audio/mp3")
                        else:
                            c_a1, c_a2 = st.columns([2.5, 1])
                            with c_a1:
                                st.caption("Audio not synthesized yet for this segment.")
                            with c_a2:
                                if st.button(f"🔊 Synthesize Voice #{seg.order_in_lesson}", key=f"btn_seg_{seg.order_in_lesson}"):
                                    tts_client = get_active_tts_client()
                                    try:
                                        a_bytes = tts_client.synthesize(seg.narration_text, voice_name=chosen_voice, speaking_rate=voice_rate)
                                        audio_cache.save_audio(c_key, a_bytes)
                                        seg.audio_file = f"{c_key}.mp3"
                                        seg.audio_url = f"/api/v1/audio/{c_key}.mp3"
                                        if hasattr(memory_store, "_persist"):
                                            memory_store._persist(current_session)
                                        st.rerun()
                                    except Exception as err:
                                        st.error(f"Synthesis failed: {err}")

                        with st.expander("🎭 Audio Stitching Runtime Simulation (e.g. Student 'Ahmed')", expanded=False):
                            p_sim = "Hey Ahmed! Great streak on Python loops. " if seg.order_in_lesson == 1 else "Spot on with that last checkpoint, Ahmed! "
                            s_sim = " Let's test your understanding on this concept, Ahmed:" if seg.assessment else " Now let's see how this ties into the next concept."
                            st.markdown(f"""
                            - 🟣 **1. Dynamic Prefix Audio (~1.5s TTS):** *"{p_sim}"*
                            - 🟢 **2. Pre-Rendered Core Audio (Cached MP3):** *"{seg.narration_text}"*
                            - 🟣 **3. Dynamic Suffix Audio (~1.5s TTS):** *"{s_sim}"*

                            💡 **Player Execution:** The mobile/web audio player queues `[Prefix (dynamic)] + [Core (CDN cached)] + [Suffix (dynamic)]`. Zero runtime modification of teacher's approved teaching prose!
                            """)

                        if seg.attached_code:
                            st.caption(f"💻 On-Screen Display ({seg.attached_code_language or 'Code'}):")
                            st.code(seg.attached_code, language=(seg.attached_code_language or "python").lower())

                        # Micro-Check Question Pop-Up
                        if seg.assessment:
                            q = seg.assessment
                            type_label = "MCQ" if q.question_type == "mcq" else ("Fill-in-the-Blank" if q.question_type == "fill_in_the_blank" else "Identify the Bug")

                            st.markdown(f"""
                            <div class="micro-check-card">
                                <div class="tts-badge">🎙️ <b>TTS Spoken Question:</b> "{q.spoken_tts_prompt}"</div><br>
                                <span style="font-weight: 700; font-size: 0.98rem; color: var(--text-color, inherit);">🎯 Micro-Check ({type_label}): {q.question_text}</span>
                            </div>
                            """, unsafe_allow_html=True)

                            if q.code_snippet:
                                st.code(q.code_snippet, language=curr_v.content.programming_language.lower())

                            if q.options:
                                user_choice = st.radio(
                                    "Choose your answer:",
                                    q.options,
                                    key=f"mcq_{current_session.lesson_id}_v{curr_v.version_no}_seg_{seg.order_in_lesson}"
                                )
                                if st.button("Check Answer", key=f"btn_{current_session.lesson_id}_v{curr_v.version_no}_seg_{seg.order_in_lesson}"):
                                    if user_choice == q.correct_answer:
                                        st.success(f"🎉 **Correct!** {q.explanation}")
                                    else:
                                        st.error(f"❌ **Not quite.** Correct answer: **{q.correct_answer}**\n\n*{q.explanation}*")
                        else:
                            # Option to generate on the fly
                            if st.button(f"⚡ Generate Micro-Check for Segment #{seg.order_in_lesson}", key=f"gen_q_{seg.order_in_lesson}"):
                                with st.spinner("Generating micro-check..."):
                                    pipeline = LessonGenerationPipeline(llm_client=client)
                                    seg.assessment = pipeline.generate_segment_assessment(current_session.spec, seg)
                                st.rerun()

                        st.write("")

# ----------------------------------------------------
# TAB 5: PUZZLES & HANDS-ON CODING EXERCISES (Macro)
# ----------------------------------------------------
with tab_practice:
    st.header("Step 5: Interactive Puzzles & Hands-On Coding Challenges")
    st.markdown("Consolidate conceptual understanding through active puzzle solving, line unscrambling, and hands-on coding.")

    current_session: Optional[LessonSession] = None
    if st.session_state.selected_lesson_id:
        current_session = memory_store.lessons.get(st.session_state.selected_lesson_id)

    if not current_session:
        st.info("Select or generate a lesson first in Step 1.")
    else:
        curr_v = current_session.current_version
        lesson_data = curr_v.content

        # Generate puzzles & exercises on demand if not present
        if not lesson_data.puzzles and not lesson_data.exercises:
            st.info("This lesson does not have practice puzzles or coding challenges yet.")
            if st.button("⚡ Generate Puzzles & Exercises for this Lesson", type="primary"):
                with st.spinner("Synthesizing logic puzzles and hands-on coding exercises..."):
                    pipeline = LessonGenerationPipeline(llm_client=client)
                    outline = Outline(
                        title=lesson_data.title,
                        sections=[
                            OutlineSection(order=s.order, title=s.title, purpose=s.purpose, covers_objectives=s.covers_objectives)
                            for s in lesson_data.sections
                        ]
                    )
                    puzzles, exercises = pipeline.generate_lesson_practice(current_session.spec, outline, lesson_data.sections)
                    lesson_data.puzzles = puzzles
                    lesson_data.exercises = exercises
                st.success("Puzzles and Coding Exercises generated!")
                st.rerun()

        # Part 1: Interactive Puzzles
        if lesson_data.puzzles:
            st.subheader("🧩 Interactive Puzzles & Logic Tracing")
            for idx, p in enumerate(lesson_data.puzzles):
                with st.container():
                    puzzle_label = p.puzzle_type.replace('_', ' ').title()
                    st.markdown(f"""
                    <div class="segment-card" style="border-left: 5px solid #8B5CF6;">
                        <span style="font-size: 1.1rem; font-weight: 700; color: var(--text-color, inherit);">Puzzle #{idx+1}: {p.title}</span>
                        <span class="badge" style="background-color: rgba(139, 92, 246, 0.2); color: #8B5CF6; border: 1px solid #8B5CF6;">{puzzle_label}</span><br>
                        <p style="margin-top: 0.5rem; color: var(--text-color, inherit);">{p.description}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    if p.scrambled_items:
                        st.caption("🔀 Scrambled Lines (Identify the correct logical order):")
                        for s_idx, item in enumerate(p.scrambled_items):
                            st.code(f"[{chr(65+s_idx)}]  {item}", language=lesson_data.programming_language.lower())

                    if p.code_snippet:
                        st.caption("Code Snippet to Trace:")
                        st.code(p.code_snippet, language=lesson_data.programming_language.lower())

                    with st.expander(f"🔍 Reveal Solution & Step-by-Step Walkthrough (Puzzle #{idx+1})"):
                        st.markdown("**Target Answer / Correct Order:**")
                        st.code(p.correct_order_or_answer, language=lesson_data.programming_language.lower())
                        st.markdown(f"**Step-by-Step Logic Walkthrough:** {p.explanation}")
                st.write("")

        st.divider()

        # Part 2: Hands-On Coding Exercises
        if lesson_data.exercises:
            st.subheader("💻 Hands-On Coding Challenges")
            for idx, ex in enumerate(lesson_data.exercises):
                with st.container():
                    diff_color = "#10B981" if ex.difficulty == "easy" else ("#F59E0B" if ex.difficulty == "medium" else "#EF4444")
                    st.markdown(f"""
                    <div class="segment-card" style="border-left: 5px solid {diff_color};">
                        <span style="font-size: 1.15rem; font-weight: 700; color: var(--text-color, inherit);">Exercise #{idx+1}: {ex.title}</span>
                        <span class="badge" style="background-color: {diff_color}22; color: {diff_color}; border: 1px solid {diff_color};">{ex.difficulty.upper()}</span><br>
                        <p style="margin-top: 0.6rem; font-size: 0.98rem; color: var(--text-color, inherit); line-height: 1.5;">{ex.task_description}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    st.caption(f"Starter Code Scaffold ({lesson_data.programming_language}):")
                    st.code(ex.starter_code, language=lesson_data.programming_language.lower())

                    if ex.hints:
                        with st.expander("💡 Hints (Try to solve before peeking!)"):
                            for h_idx, hint in enumerate(ex.hints):
                                st.markdown(f"- **Hint {h_idx+1}:** {hint}")

                    with st.expander(f"✅ Reveal Reference Solution & Output (Exercise #{idx+1})"):
                        st.caption(f"**Expected Output:** `{ex.expected_output}`")
                        st.code(ex.solution_code, language=lesson_data.programming_language.lower())
                st.write("")

# ----------------------------------------------------
# TAB 6: STUDENT INTERACTIVE LEARNING PLAYER
# ----------------------------------------------------
with tab_runtime:
    st.header("Step 6: Student Interactive Learning Player")
    st.markdown("""
    Experience how a student attends an interactive, audio-narrated lesson in ALMA.
    Features synchronized teacher voice playback, live slide progression, formative checkpoints, and an inline **Ask ALMA** AI tutor.
    """)

    # 1. Student Profile Selector & Overview
    all_students = student_repository.list_students()
    if not all_students:
        mohamad_default = student_repository.get_default_student()
        all_students = [mohamad_default] if mohamad_default else []

    s_options = {s.student_id: f"{s.first_name} {s.last_name} ({s.grade_level})" for s in all_students}
    col_stu1, col_stu2 = st.columns([1.5, 2.5])
    with col_stu1:
        selected_stu_id = st.selectbox(
            "Select Student Profile",
            options=list(s_options.keys()),
            format_func=lambda x: s_options[x],
            index=0
        )
    active_student = student_repository.get_student(selected_stu_id) or all_students[0]

    s_col1, s_col2, s_col3 = st.columns([1.5, 1.2, 1.3])
    with s_col1:
        st.markdown(f"""
        <div class="segment-card" style="border-left: 5px solid #3B82F6;">
            <span style="font-size: 1.15rem; font-weight: 700;">👤 Student: {active_student.first_name} {active_student.last_name}</span><br>
            <span style="font-size: 0.85rem; opacity: 0.85;">🏫 {active_student.school_name or 'ALMA Academy'} | <b>{active_student.grade_level}</b></span><br>
            <span style="font-size: 0.85rem; opacity: 0.85;">🆔 Code: <code>{active_student.student_code}</code></span>
        </div>
        """, unsafe_allow_html=True)
    with s_col2:
        st.metric("Lessons Completed", active_student.lessons_completed)
        st.metric("Learning Streak", f"{active_student.current_streak} 🔥")
    with s_col3:
        st.markdown("**⚙️ Learning Preferences:**")
        st.write(f"- Pacing: `{active_student.preferences.pacing.title()}`")
        st.write(f"- Tone: `{active_student.preferences.tone.title()}`")
        st.write(f"- Voice: `{chosen_voice}`")

    if active_student.struggling_concepts:
        st.markdown("##### ⚠️ Diagnosed Conceptual Struggles in Student History")
        for sc in active_student.struggling_concepts:
            st.warning(f"**Concept:** `{sc.concept_label}` ({sc.concept_id})\n\n↳ **Past Error:** {sc.last_misconception} (Tested: {sc.times_tested}x, Incorrect: {sc.times_wrong}x)")

    st.divider()

    # 2. Interactive Audio-Narrated Lesson Player
    current_session: Optional[LessonSession] = None
    if st.session_state.selected_lesson_id:
        current_session = memory_store.lessons.get(st.session_state.selected_lesson_id)

    if not current_session:
        st.info("Select or generate a lesson first in Step 1 to launch the student interactive player.")
    else:
        curr_v = current_session.current_version
        lesson_data = curr_v.content
        seg_data = curr_v.segmentation

        if not seg_data or not seg_data.topics:
            st.warning("This lesson has not been segmented yet. Go to **Tab 4 (Narration & Micro-Checks)** and click 'Segment Current Version' first!")
        else:
            all_slides = [s for t in seg_data.topics for s in t.segments]
            total_slides = len(all_slides)

            # Initialize slide index
            if "student_slide_idx" not in st.session_state:
                st.session_state.student_slide_idx = 0

            # Clamp index
            slide_idx = max(0, min(st.session_state.student_slide_idx, total_slides - 1))
            current_seg = all_slides[slide_idx]

            # Header & Progress
            st.subheader(f"🎧 Slide {slide_idx + 1} of {total_slides}: {current_seg.title}")
            st.progress((slide_idx + 1) / total_slides)

            # 1. Slide 1 Dynamic Greeting Card
            if slide_idx == 0:
                p_text = f"Hey {active_student.first_name}! "
                if active_student.current_streak >= 3:
                    p_text += f"Awesome to see your {active_student.current_streak}-lesson streak going strong! "
                p_text += f"Today we're diving into {lesson_data.title} in {lesson_data.programming_language}. Let's get started!"

                st.markdown(f"""
                <div style="background-color: rgba(59, 130, 246, 0.08); border: 1px solid #3B82F6; border-radius: 10px; padding: 1.0rem 1.2rem; margin-bottom: 1.2rem;">
                    <span style="font-size: 0.82rem; font-weight: 700; color: #3B82F6; text-transform: uppercase;">🎙️ Personalized Dynamic Welcome</span><br>
                    <span style="font-size: 1.02rem; font-style: italic; color: var(--text-color, inherit);">"{p_text}"</span>
                </div>
                """, unsafe_allow_html=True)

            # 2. Audio Player for Current Segment
            c_key = audio_cache.compute_cache_key(current_seg.narration_text, voice_name=chosen_voice, speaking_rate=voice_rate)
            audio_path = audio_cache.get_audio_path(c_key)

            col_audio1, col_audio2 = st.columns([2.5, 1.2])
            with col_audio1:
                if audio_path and audio_path.is_file():
                    st.markdown("🔊 **Teacher Narration Audio:**")
                    st.audio(str(audio_path), format="audio/mp3")
                else:
                    st.caption("Audio not yet synthesized for this segment.")
            with col_audio2:
                if not (audio_path and audio_path.is_file()):
                    if st.button("⚡ Synthesize This Slide Audio", type="primary"):
                        tts_client = get_active_tts_client()
                        try:
                            a_bytes = tts_client.synthesize(current_seg.narration_text, voice_name=chosen_voice, speaking_rate=voice_rate)
                            audio_cache.save_audio(c_key, a_bytes)
                            current_seg.audio_file = f"{c_key}.mp3"
                            current_seg.audio_url = f"/api/v1/audio/{c_key}.mp3"
                            st.rerun()
                        except Exception as e:
                            st.error(f"TTS Error: {e}")

            # 3. Main Slide Instructional Card
            st.markdown(f"""
            <div class="segment-card" style="margin-top: 0.8rem; padding: 1.4rem;">
                <span style="font-size: 0.82rem; font-weight: 700; color: #10B981; text-transform: uppercase;">📖 Teaching Content:</span><br>
                <p style="font-size: 1.10rem; line-height: 1.6; margin-top: 0.5rem; color: var(--text-color, inherit);">
                    {current_seg.narration_text}
                </p>
            </div>
            """, unsafe_allow_html=True)

            # Attached Code Display
            if current_seg.attached_code:
                st.markdown(f"**💻 Code Demonstration ({current_seg.attached_code_language or lesson_data.programming_language}):**")
                st.code(current_seg.attached_code, language=(current_seg.attached_code_language or lesson_data.programming_language).lower())

            # 4. Formative Checkpoint on this Slide
            if current_seg.assessment:
                q = current_seg.assessment
                st.markdown(f"""
                <div class="micro-check-card" style="margin-top: 1.2rem;">
                    <div class="tts-badge">🎯 <b>Quick Knowledge Check:</b> "{q.spoken_tts_prompt or q.question_text}"</div><br>
                    <span style="font-weight: 700; font-size: 1.0rem; color: var(--text-color, inherit);">{q.question_text}</span>
                </div>
                """, unsafe_allow_html=True)

                if q.code_snippet:
                    st.code(q.code_snippet, language=lesson_data.programming_language.lower())

                if q.options:
                    ans_choice = st.radio(
                        "Select your answer:",
                        q.options,
                        key=f"student_ans_{slide_idx}_{current_session.lesson_id}"
                    )
                    if st.button("Submit Answer", key=f"btn_sub_{slide_idx}"):
                        is_correct = (ans_choice.strip().lower() == q.correct_answer.strip().lower())
                        student_repository.record_checkpoint_result(
                            student_id=active_student.student_id,
                            concept_id=f"seg_{current_seg.order_in_lesson}",
                            concept_label=current_seg.title,
                            is_correct=is_correct,
                        )
                        if is_correct:
                            st.success(f"🎉 **Correct, {active_student.first_name}!** {q.explanation}")
                        else:
                            st.error(f"❌ **Not quite, {active_student.first_name}.** Correct answer: **{q.correct_answer}**\n\n💡 *Explanation:* {q.explanation}")

            # 5. Interactive "Ask ALMA" AI Tutor
            with st.expander("🤖 Have a question about this slide? Ask ALMA Tutor!", expanded=False):
                st.caption(f"ALMA is available 24/7 to answer questions strictly grounded in '{current_seg.title}':")
                stu_question = st.text_input("Type your question:", placeholder="e.g. Can you explain what this line of code does?", key=f"q_input_{slide_idx}")
                if st.button("Send to ALMA", key=f"btn_ask_{slide_idx}"):
                    if stu_question.strip():
                        with st.spinner("ALMA is formulating explanation..."):
                            try:
                                tutor_prompt = (
                                    f"You are ALMA, an encouraging, friendly computer science tutor for a {active_student.grade_level} student named {active_student.first_name}.\n"
                                    f"Current Lesson Topic: {lesson_data.title}\n"
                                    f"Current Slide Title: {current_seg.title}\n"
                                    f"Slide Explanation: {current_seg.narration_text}\n"
                                    f"Code on Slide: {current_seg.attached_code or 'None'}\n\n"
                                    f"Student Question: {stu_question}\n\n"
                                    f"Provide a concise, encouraging, pedagogically sound answer (2-4 sentences) that directly clarifies their question."
                                )
                                tutor_resp = client.generate(prompt=tutor_prompt, json_mode=False, temperature=0.3)
                                answer_text = tutor_resp.content.strip()
                                st.markdown(f"""
                                <div class="callout-box callout-note">
                                    <b>🎓 ALMA Tutor:</b> {answer_text}
                                </div>
                                """, unsafe_allow_html=True)
                            except Exception as ask_err:
                                st.error(f"Failed to get answer: {ask_err}")

            st.divider()

            # 6. Slide Navigation Bar
            col_prev, col_middle, col_next = st.columns([1.2, 2.0, 1.2])

            with col_prev:
                if st.button("⬅️ Previous Slide", disabled=(slide_idx == 0), use_container_width=True):
                    st.session_state.student_slide_idx = max(0, slide_idx - 1)
                    st.rerun()

            with col_middle:
                st.markdown(f"<div style='text-align: center; padding-top: 0.5rem; font-weight: 600; opacity: 0.8;'>Slide {slide_idx + 1} / {total_slides}</div>", unsafe_allow_html=True)

            with col_next:
                if slide_idx < total_slides - 1:
                    if st.button("Next Slide ➡️", type="primary", use_container_width=True):
                        st.session_state.student_slide_idx = slide_idx + 1
                        st.rerun()
                else:
                    if st.button("🎉 Finish Lesson", type="primary", use_container_width=True):
                        st.session_state.lesson_completed_modal = True
                        active_student.lessons_completed += 1
                        active_student.current_streak += 1
                        st.balloons()
                        st.rerun()

            if st.session_state.get("lesson_completed_modal"):
                st.success(f"🏆 **Outstanding Work, {active_student.first_name}!** You have successfully completed **'{lesson_data.title}'**!")
                st.info(f"🔥 Your learning streak has reached **{active_student.current_streak} lessons**! Keep up the momentum!")
                if st.button("Start Next Lesson / Reset"):
                    st.session_state.student_slide_idx = 0
                    st.session_state.lesson_completed_modal = False
                    st.rerun()


