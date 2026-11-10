import json
import re
import time
from typing import Optional, Dict, Any
from openai import OpenAI
import structlog
from .interface import BaseLLMClient, LLMResponse
from ..config import config

logger = structlog.get_logger(__name__)

class OpenRouterLLMClient(BaseLLMClient):
    """OpenRouter backup client adapter using openai SDK."""

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        key = api_key or config.openrouter_api_key
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=key or "missing-key"
        ) if key else None
        self.default_model = default_model or config.default_openrouter_model

    def _clean_json_text(self, text: str) -> str:
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
        if not self.client:
            raise ValueError("OpenRouter API key is not configured. Set OPENROUTER_API_KEY in your .env file.")

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
                    raise ValueError(f"Failed to parse OpenRouter output as JSON: {err}\nOutput was:\n{raw_content}")

        usage = getattr(completion, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

        logger.info(
            "llm_call_completed",
            provider="openrouter",
            model=chosen_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=round(elapsed_ms, 2),
        )

        return LLMResponse(
            content=raw_content,
            parsed_json=parsed_json,
            model_name=chosen_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=elapsed_ms,
        )
