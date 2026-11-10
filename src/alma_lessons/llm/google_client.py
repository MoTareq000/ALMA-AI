import json
import re
import time
from typing import Optional, Dict, Any
import requests

from .interface import BaseLLMClient, LLMResponse
from ..config import config


class GoogleGeminiLLMClient(BaseLLMClient):
    """Google Gemini client adapter using direct Google Generative Language REST API."""

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        self.api_key = api_key or config.gemini_api_key
        self.default_model = default_model or config.default_gemini_model or config.default_generator_model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def _clean_json_text(self, text: str) -> str:
        """Strip markdown code fence blocks if returned by model."""
        text = text.strip()
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if fence_match:
            return fence_match.group(1).strip()
        return text

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = True,
        temperature: float = 0.3,
        model: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        if not self.api_key:
            raise ValueError("Google Gemini API key is not configured. Set GEMINI_API_KEY in your .env file.")

        chosen_model = model or self.default_model
        clean_model_id = chosen_model.replace("models/", "")

        endpoint_url = f"{self.base_url}/{clean_model_id}:generateContent"
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        contents = [{"parts": [{"text": prompt}]}]
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }

        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        max_retries = 3
        response = None
        elapsed_ms = 0.0

        for attempt in range(max_retries):
            start_time = time.perf_counter()
            response = requests.post(endpoint_url, headers=headers, json=payload, timeout=60)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            if response.status_code in (429, 503) and attempt < max_retries - 1:
                # Rate limited or temporary unavailable: brief exponential backoff
                time.sleep(2.0 * (attempt + 1))
                continue
            elif response.status_code != 200:
                raise ValueError(f"Google Gemini API error ({response.status_code}): {response.text}")
            break

        res_json = response.json()
        candidates = res_json.get("candidates", [])
        if not candidates:
            raise ValueError(f"Google Gemini returned no candidates: {res_json}")

        parts = candidates[0].get("content", {}).get("parts", [])
        raw_content = parts[0].get("text", "") if parts else ""

        parsed_json = None
        if json_mode:
            cleaned = self._clean_json_text(raw_content)
            try:
                parsed_json = json.loads(cleaned)
            except Exception:
                try:
                    import json_repair
                    parsed_json = json_repair.loads(cleaned)
                    if not isinstance(parsed_json, (dict, list)):
                        raise ValueError(f"json_repair did not return a dict or list: {parsed_json}")
                except Exception as err:
                    raise ValueError(f"Failed to parse Gemini output as JSON: {err}\nOutput was:\n{raw_content}")

        usage = res_json.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        completion_tokens = usage.get("candidatesTokenCount", 0)

        return LLMResponse(
            content=raw_content,
            parsed_json=parsed_json,
            model_name=clean_model_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=elapsed_ms,
        )
