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

    # LLM - OpenAI 兼容接口（支持小米 MiMo、OpenRouter、本地部署等）
    llm_api_key: str = ""
    llm_base_url: str = "https://openrouter.ai/api/v1"

    # 各 Agent 默认模型 ID
    model_planner: str = "mimo-7b"
    model_writer: str = "mimo-7b"
    model_consistency: str = "mimo-7b"
    model_reviewer: str = "mimo-7b"
    model_rewrite: str = "mimo-7b"
    model_context: str = "mimo-7b"

    # Object Storage (OSS)
    oss_endpoint: str = ""
    oss_access_key: str = ""
    oss_secret_key: str = ""
    oss_bucket: str = "dreamweaver"

    # Chroma (向量数据库)
    chroma_host: str = "localhost"
    chroma_port: int = 8100


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
