from typing import Optional
from ..config import config
from ..llm import BaseLLMClient, GoogleGeminiLLMClient, GroqLLMClient, OpenRouterLLMClient, FakeLLMClient
from ..storage import memory_store, student_repository, job_manager

def get_llm_client(provider: Optional[str] = "gemini", model: Optional[str] = None) -> BaseLLMClient:
    """Factory dependency to instantiate appropriate LLM client based on requested provider."""
    # Sanitize inputs (handles Swagger UI default "string" placeholder)
    provider_str = (provider or "").strip().lower()
    if not provider_str or provider_str in ("string", "default", "none", "null"):
        provider_str = "gemini"

    model_clean = (model or "").strip()
    if not model_clean or model_clean.lower() in ("string", "default", "none", "null"):
        model_clean = None

    if "gemini" in provider_str or "google" in provider_str:
        return GoogleGeminiLLMClient(
            api_key=config.gemini_api_key,
            default_model=model_clean or config.default_generator_model
        )
    elif "groq" in provider_str:
        return GroqLLMClient(
            api_key=config.groq_api_key,
            default_model=model_clean or "llama-3.3-70b-versatile"
        )
    elif "openrouter" in provider_str:
        return OpenRouterLLMClient(
            api_key=config.openrouter_api_key,
            default_model=model_clean or "google/gemini-2.5-flash"
        )
    elif "fake" in provider_str:
        return FakeLLMClient()

    # Default fallback to Gemini
    return GoogleGeminiLLMClient(
        api_key=config.gemini_api_key,
        default_model=model_clean or config.default_generator_model
    )
