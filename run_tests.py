import sys
from pathlib import Path

# Add src and root directory to python path
root = Path(__file__).resolve().parent
sys.path.insert(0, str(root / "src"))
sys.path.insert(0, str(root))

print("=== Running ALMA AI Lesson Pipeline Test Suite ===")

import tests.test_domain as t_domain
t_domain.test_lesson_spec_creation()
t_domain.test_lesson_content_word_and_block_count()
t_domain.test_state_transitions()
t_domain.test_assessment_models()
print("[PASS] Domain & Assessment tests: PASSED")

import tests.test_validation as t_val
t_val.test_schema_validator_valid()
t_val.test_structure_validator_catches_empty_and_placeholders()
t_val.test_validation_runner()
print("[PASS] Validation tests: PASSED")


import tests.test_generation as t_gen
t_gen.test_generation_pipeline_two_pass_with_fake_llm()
print("[PASS] Generation two-pass tests: PASSED")

import tests.test_segmentation as t_seg
t_seg.test_basic_lesson_segmenter()
t_seg.test_topic_assessment_generator()
print("[PASS] Basic segmentation tests: PASSED")

import tests.test_storage as t_store
t_store.test_memory_store_lifecycle_and_json_export_import()
t_store.test_mongo_schema_alignment_and_bidirectional_conversion()
t_store.test_session_repository_and_job_manager()
print("[PASS] In-memory & MongoDB schema alignment tests: PASSED")

import tests.test_google_client as t_goog
t_goog.test_google_client_init()
t_goog.test_google_client_generate_json()
print("[PASS] Google Gemini Client tests: PASSED")

import tests.test_curriculum as t_curr
t_curr.test_extract_text_from_pdf()
t_curr.test_extract_curriculum_from_pdf()
t_curr.test_lesson_spec_with_scope_notes()
print("[PASS] Curriculum PDF Extractor tests: PASSED")

import tests.test_api as t_api
t_api.test_health_endpoint()
t_api.test_student_profile_endpoint()
t_api.test_lessons_endpoints_crud_and_runtime()
print("[PASS] FastAPI REST Endpoints & Runtime tests: PASSED")

print("\n=== ALL TESTS PASSED SUCCESSFULLY! ===")

