from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql+asyncpg://moodlepro:moodlepro@localhost:5432/moodlepro"
    redis_url: str = "redis://localhost:6379/0"
    internal_api_token: str = "dev-internal-token-change-me"
    storage_dir: str = "./data"
    public_base_url: str = "http://localhost:8000"

    # Groq cloud fallback: used when no cluster GPU worker claims a queued job in time.
    groq_api_key: str = ""
    groq_model: str = "whisper-large-v3"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_fallback_grace_seconds: float = 90.0
    groq_fallback_poll_seconds: float = 2.0


settings = Settings()
