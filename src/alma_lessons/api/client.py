import time
from typing import Dict, Any, List, Optional
import requests

class AlmaApiClient:
    """HTTP Client for communicating with the ALMA FastAPI backend service."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000/api/v1"):
        self.base_url = base_url.rstrip("/")

    def is_healthy(self) -> bool:
        """Check if FastAPI backend is online and reachable."""
        try:
            r = requests.get(f"{self.base_url}/health", timeout=1.5)
            return r.status_code == 200
        except Exception:
            return False

    def get_health(self) -> Dict[str, Any]:
        """Fetch health metadata from backend."""
        r = requests.get(f"{self.base_url}/health", timeout=3)
        r.raise_for_status()
        return r.json()

    # --- Lesson Generation & Management ---
    def generate_lesson(self, spec_dict: Dict[str, Any], provider: str = "gemini", model: Optional[str] = None) -> Dict[str, Any]:
        """Trigger async lesson generation."""
        payload = {
            "spec": spec_dict,
            "provider": provider,
            "model": model
        }
        r = requests.post(f"{self.base_url}/lessons/generate", json=payload, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_job(self, job_id: str) -> Dict[str, Any]:
        """Poll status of an asynchronous generation job (supports both /jobs/{id} and /lesson-generations/job/{id})."""
        r = requests.get(f"{self.base_url}/jobs/{job_id}", timeout=5)
        if r.status_code == 404:
            r = requests.get(f"{self.base_url}/lesson-generations/job/{job_id}", timeout=5)
        r.raise_for_status()
        return r.json()

    def poll_job_until_complete(self, job_id: str, poll_interval: float = 1.0, max_timeout: float = 180.0, callback=None) -> Dict[str, Any]:
        """Helper to poll job until completed or failed."""
        start_time = time.time()
        while time.time() - start_time < max_timeout:
            job = self.get_job(job_id)
            status = job.get("status")
            if callback:
                callback(job.get("step_message", "Processing..."), job.get("progress_percent", 0.0))

            if status == "completed":
                return job
            elif status == "failed":
                raise RuntimeError(f"Generation job failed: {job.get('error', 'Unknown error')}")

            time.sleep(poll_interval)
        raise TimeoutError("Generation job timed out while waiting for completion")

    def list_lessons(self) -> List[Dict[str, Any]]:
        """List all lessons in backend (lightweight summary)."""
        r = requests.get(f"{self.base_url}/lessons", timeout=5)
        r.raise_for_status()
        return r.json()

    def get_lesson(self, lesson_id: str) -> Dict[str, Any]:
        """Fetch full lesson details, content, validation report, and segmentation."""
        r = requests.get(f"{self.base_url}/lessons/{lesson_id}", timeout=5)
        r.raise_for_status()
        return r.json()

    def sync_all_lessons(self) -> Dict[str, Any]:
        """Fetch all lesson sessions from backend for client cache synchronization."""
        r = requests.get(f"{self.base_url}/lessons/sync/all", timeout=10)
        r.raise_for_status()
        return r.json()

    def edit_lesson(self, lesson_id: str, title: str, sections: list, intro: Optional[list] = None, concl: Optional[list] = None) -> Dict[str, Any]:
        """Teacher edit: creates an immutable new version."""
        payload = {
            "title": title,
            "sections": sections,
            "introduction": intro,
            "conclusion": concl
        }
        r = requests.put(f"{self.base_url}/lessons/{lesson_id}/edit", json=payload, timeout=20)
        r.raise_for_status()
        return r.json()

    def approve_lesson(self, lesson_id: str, acknowledged_warnings: Optional[List[str]] = None) -> Dict[str, Any]:
        """Approve the current lesson version."""
        payload = {"acknowledged_warnings": acknowledged_warnings or []}
        r = requests.post(f"{self.base_url}/lessons/{lesson_id}/approve", json=payload, timeout=5)
        r.raise_for_status()
        return r.json()

    def reject_lesson(self, lesson_id: str, reason: str) -> Dict[str, Any]:
        """Reject the current lesson version."""
        payload = {"rejection_reason": reason}
        r = requests.post(f"{self.base_url}/lessons/{lesson_id}/reject", json=payload, timeout=5)
        r.raise_for_status()
        return r.json()

    def regenerate_lesson(self, lesson_id: str, feedback: str, provider: str = "gemini", model: Optional[str] = None) -> Dict[str, Any]:
        """Trigger AI regeneration job with teacher feedback notes."""
        payload = {
            "teacher_feedback": feedback,
            "provider": provider,
            "model": model
        }
        r = requests.post(f"{self.base_url}/lessons/{lesson_id}/regenerate", json=payload, timeout=10)
        r.raise_for_status()
        return r.json()

    # --- Student Runtime Methods ---
    def get_student(self, student_id: str = "student_mohamad_001") -> Dict[str, Any]:
        """Get student profile."""
        r = requests.get(f"{self.base_url}/runtime/students/{student_id}", timeout=5)
        r.raise_for_status()
        return r.json()

    def start_student_session(self, lesson_id: str, student_id: str = "student_mohamad_001") -> Dict[str, Any]:
        """Start adaptive lesson session for a student."""
        payload = {"student_id": student_id}
        r = requests.post(f"{self.base_url}/runtime/lessons/{lesson_id}/start", json=payload, timeout=5)
        r.raise_for_status()
        return r.json()

    def answer_checkpoint(self, lesson_id: str, section_order: int, selected_answer: str, student_id: str = "student_mohamad_001", session_id: Optional[str] = None) -> Dict[str, Any]:
        """Submit diagnostic checkpoint answer."""
        payload = {
            "session_id": session_id,
            "student_id": student_id,
            "section_order": section_order,
            "selected_option": selected_answer
        }
        r = requests.post(f"{self.base_url}/runtime/lessons/{lesson_id}/checkpoints/answer", json=payload, timeout=5)
        r.raise_for_status()
        return r.json()

    def ask_alma(self, lesson_id: str, section_order: int, question_text: str, student_id: str = "student_mohamad_001", session_id: Optional[str] = None) -> Dict[str, Any]:
        """Submit question to Ask ALMA tutor."""
        payload = {
            "session_id": session_id,
            "student_id": student_id,
            "current_section_order": section_order,
            "question_text": question_text
        }
        r = requests.post(f"{self.base_url}/runtime/lessons/{lesson_id}/ask-alma", json=payload, timeout=10)
        r.raise_for_status()
        return r.json()
