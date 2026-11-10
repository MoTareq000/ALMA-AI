from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

class PipelineConfig(BaseSettings):
    """Central configuration for ALMA AI Lesson Generation Pipeline.
    Single source of truth for runtime defaults, models, storage, and security.
    """
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # API Keys
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")

    # LLM Models & Providers
    default_provider: str = Field(default="google", alias="DEFAULT_PROVIDER")
    default_generator_model: str = Field(default="gemini-3.5-flash-lite", alias="DEFAULT_GENERATOR_MODEL")
    default_judge_model: str = Field(default="gemini-3.5-flash-lite", alias="DEFAULT_JUDGE_MODEL")  # Reserved, not used yet
    default_bridge_model: str = Field(default="gemini-3.5-flash-lite", alias="DEFAULT_BRIDGE_MODEL")
    default_gemini_model: str = Field(default="gemini-3.5-flash-lite", alias="DEFAULT_GEMINI_MODEL")
    default_groq_model: str = Field(default="llama-3.3-70b-versatile", alias="DEFAULT_GROQ_MODEL")
    default_openrouter_model: str = Field(default="google/gemini-2.5-flash", alias="DEFAULT_OPENROUTER_MODEL")

    default_words_per_minute: int = Field(default=140, alias="DEFAULT_WORDS_PER_MINUTE")
    prompt_dir: Path = Field(default=ROOT_DIR / "prompts" / "v1")

    # Storage Settings
    mongodb_uri: str = Field(default="mongodb://127.0.0.1:27017", alias="MONGODB_URI")
    mongodb_db_name: str = Field(default="ALMA", alias="MONGODB_DB_NAME")
    use_mongodb: bool = Field(default=True, alias="USE_MONGODB")
    require_mongodb: bool = Field(default=False, alias="REQUIRE_MONGODB")

    # Security & Guardrails
    allowed_origins: str = Field(default="http://localhost:3000,http://localhost:5000", alias="ALLOWED_ORIGINS")
    alma_api_keys: str = Field(default="", alias="ALMA_API_KEYS")
    alma_auth_disabled: bool = Field(default=True, alias="ALMA_AUTH_DISABLED")
    max_upload_mb: int = Field(default=10, alias="MAX_UPLOAD_MB")
    rate_limit_per_hour: int = Field(default=10, alias="RATE_LIMIT_PER_HOUR")
    max_active_generations: int = Field(default=5, alias="MAX_ACTIVE_GENERATIONS")

    # Runtime Data & Job Backend
    alma_seed_demo_data: bool = Field(default=False, alias="ALMA_SEED_DEMO_DATA")
    job_backend: str = Field(default="inprocess", alias="JOB_BACKEND")  # "inprocess" or "rq"
    redis_url: str = Field(default="redis://127.0.0.1:6379/0", alias="REDIS_URL")

    # Text-to-Speech (Google Cloud TTS) Settings
    gcp_tts_api_key: str = Field(default="", alias="GCP_TTS_API_KEY")
    tts_voice_name: str = Field(default="en-US-Journey-F", alias="TTS_VOICE_NAME")
    tts_speaking_rate: float = Field(default=1.0, alias="TTS_SPEAKING_RATE")
    audio_cache_dir: Path = Field(default=ROOT_DIR / "data" / "audio", alias="AUDIO_CACHE_DIR")

config = PipelineConfig()
