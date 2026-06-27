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

    # LLM - OpenRouter 多模型聚合（OpenAI 兼容接口）
    # llm_api_key = OpenRouter API Key（一个 key 调所有模型）
    # 也可指向其他 OpenAI 兼容网关/本地部署，改 llm_base_url 即可
    llm_api_key: str = ""
    llm_base_url: str = "https://openrouter.ai/api/v1"

    # OpenRouter 推荐请求头（用于其用量归因/排行榜，可留空）
    openrouter_referer: str = ""
    openrouter_title: str = "DreamWeaver"

    # ── 各 Agent 模型路由（混合策略，全部可用环境变量覆盖）──
    # 主模型 + 失败时的 fallback 备用模型；slug 以 https://openrouter.ai/models 为准
    # 规划/写作/评审/重写：质量优先；一致性/上下文抽取：低成本
    # Stage-level LLM routing. Empty values fall back to the legacy agent-level keys below.
    model_blueprint: str = ""
    model_blueprint_fallback: str = ""
    model_outline: str = ""
    model_outline_fallback: str = ""
    model_draft: str = ""
    model_draft_fallback: str = ""
    model_review: str = ""
    model_review_fallback: str = ""
    model_repair: str = ""
    model_repair_fallback: str = ""
    model_memory_extract: str = ""
    model_memory_extract_fallback: str = ""

    # Legacy agent-level LLM routing. Kept for backwards-compatible .env files.
    model_planner: str = "anthropic/claude-3.5-sonnet"
    model_planner_fallback: str = "openai/gpt-4o"
    model_writer: str = "anthropic/claude-3.5-sonnet"
    model_writer_fallback: str = "deepseek/deepseek-chat"
    model_consistency: str = "openai/gpt-4o-mini"
    model_consistency_fallback: str = "deepseek/deepseek-chat"
    model_reviewer: str = "anthropic/claude-3.5-sonnet"
    model_reviewer_fallback: str = "openai/gpt-4o"
    model_rewrite: str = "anthropic/claude-3.5-sonnet"
    model_rewrite_fallback: str = "openai/gpt-4o"
    model_context: str = "deepseek/deepseek-chat"
    model_context_fallback: str = "openai/gpt-4o-mini"

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
