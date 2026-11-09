from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class LLMResponse(BaseModel):
    """Normalized response from any LLM provider."""
    content: str
    parsed_json: Optional[Dict[str, Any]] = None
    model_name: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0

class BaseLLMClient(ABC):
    """Abstract client interface for interacting with LLM providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = True,
        temperature: float = 0.3,
        model: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate a response from the model."""
        pass
