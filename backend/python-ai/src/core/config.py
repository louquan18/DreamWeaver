"""应用配置管理"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，通过环境变量或 .env 文件加载"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "DreamWeaver AI Service"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database (PostgreSQL)
    database_url: str = "postgresql+asyncpg://dreamweaver:dreamweaver@localhost:5432/dreamweaver"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LLM / OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Default model for each agent type
    model_planner: str = "anthropic/claude-sonnet-4-20250514"
    model_writer: str = "anthropic/claude-sonnet-4-20250514"
    model_consistency: str = "openai/gpt-4o-mini"
    model_reviewer: str = "anthropic/claude-sonnet-4-20250514"
    model_rewrite: str = "anthropic/claude-sonnet-4-20250514"
    model_context: str = "openai/gpt-4o-mini"

    # Object Storage (OSS)
    oss_endpoint: str = ""
    oss_access_key: str = ""
    oss_secret_key: str = ""
    oss_bucket: str = "dreamweaver"

    # Chroma
    chroma_host: str = "localhost"
    chroma_port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
