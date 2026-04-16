"""MARAMARA - Application configuration via pydantic-settings."""
from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ----- App -----
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    secret_key: str = Field(default="dev-secret-change-in-production")
    log_level: str = "INFO"

    # ----- Supabase -----
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_project_ref: str
    supabase_jwt_secret: str = ""

    # ----- Database -----
    database_url: str

    # ----- Redis -----
    redis_url: str = "redis://localhost:6379/0"

    # ----- LLM keys -----
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""

    # ----- CrewAI -----
    crewai_model: str = "claude-sonnet-4-6"
    crewai_telemetry_opt_out: bool = True

    # ----- ML models -----
    vad_model: str = "silero"
    vad_threshold: float = 0.5
    speaker_model: str = "speechbrain/spkrec-ecapa-voxceleb"
    speaker_similarity_threshold: float = 0.75
    whisper_model: str = "large-v3"
    whisper_device: Literal["cpu", "cuda"] = "cpu"
    whisper_compute_type: str = "int8"

    # ----- Audio -----
    audio_chunk_duration_sec: int = 10
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    enrollment_min_duration_sec: int = 30
    enrollment_max_duration_sec: int = 45

    # ----- Features -----
    retain_raw_audio: bool = False
    enable_realtime: bool = True
    enable_crewai_insights: bool = True

    # ----- i18n -----
    supported_languages: str = "he,en"
    default_language: str = "he"

    @property
    def supported_languages_list(self) -> list[str]:
        return [lang.strip() for lang in self.supported_languages.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
