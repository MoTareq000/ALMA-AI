from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

class PipelineConfig(BaseSettings):
    """Central configuration for ALMA AI Lesson Generation Pipeline."""
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")

    default_provider: str = Field(default="google", alias="DEFAULT_PROVIDER")
    default_generator_model: str = Field(default="gemini-3.5-flash-lite", alias="DEFAULT_GENERATOR_MODEL")
    default_judge_model: str = Field(default="gemini-3.5-flash-lite", alias="DEFAULT_JUDGE_MODEL")
    default_bridge_model: str = Field(default="gemini-3.5-flash-lite", alias="DEFAULT_BRIDGE_MODEL")
    default_gemini_model: str = Field(default="gemini-3.5-flash-lite", alias="DEFAULT_GEMINI_MODEL")

    default_words_per_minute: int = Field(default=140, alias="DEFAULT_WORDS_PER_MINUTE")
    prompt_dir: Path = Field(default=ROOT_DIR / "prompts" / "v1")

    # MongoDB Settings
    mongodb_uri: str = Field(default="mongodb://127.0.0.1:27017", alias="MONGODB_URI")
    mongodb_db_name: str = Field(default="ALMA", alias="MONGODB_DB_NAME")
    use_mongodb: bool = Field(default=True, alias="USE_MONGODB")

config = PipelineConfig()
