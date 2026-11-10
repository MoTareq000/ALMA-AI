import json
import re
import time
from typing import Optional, Dict, Any
from groq import Groq
from .interface import BaseLLMClient, LLMResponse
from ..config import config

class GroqLLMClient(BaseLLMClient):
    """Groq client adapter using official groq SDK."""

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        key = api_key or config.groq_api_key
        self.client = Groq(api_key=key) if key else None
        self.default_model = default_model or config.default_groq_model

    def _clean_json_text(self, text: str) -> str:
        """Strip markdown code fence blocks if returned by model."""
        text = text.strip()
        # Remove ```json ... ``` or ``` ... ```
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
        if not self.client:
            raise ValueError("Groq API key is not configured. Set GROQ_API_KEY in your .env file.")

        chosen_model = model or self.default_model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs: Dict[str, Any] = {
            "model": chosen_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        start_time = time.perf_counter()
        completion = self.client.chat.completions.create(**kwargs)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        raw_content = completion.choices[0].message.content or ""
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
                    raise ValueError(f"Failed to parse model output as JSON: {err}\nOutput was:\n{raw_content}")

        usage = getattr(completion, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

        return LLMResponse(
            content=raw_content,
            parsed_json=parsed_json,
            model_name=chosen_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=elapsed_ms,
        )
