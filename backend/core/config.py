"""
Centralised settings — loaded from .env via pydantic-settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM API Keys
    GROQ_API_KEY:     str = ""
    CEREBRAS_API_KEY: str = ""
    MISTRAL_API_KEY:  str = ""

    # Database
    DATABASE_URL: str = "sqlite:///./data/observatory.db"

    # App
    APP_ENV:   str = "development"
    LOG_LEVEL: str = "INFO"

    # Alert thresholds
    HALLUCINATION_ALERT_THRESHOLD: float = 0.5   # below = alert
    LATENCY_ALERT_THRESHOLD_MS:    float = 5000  # above = alert


settings = Settings()