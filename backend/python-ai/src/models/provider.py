"""LLM Provider 抽象层

统一封装 OpenAI 兼容接口，支持小米 MiMo / OpenRouter / 本地部署等。
"""

from collections.abc import AsyncIterator
from functools import lru_cache

from langchain_openai import ChatOpenAI
from loguru import logger

from src.core.config import settings


def get_llm(
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    streaming: bool = False,
) -> ChatOpenAI:
    """
    获取 LLM 实例

    Args:
        model: 模型 ID，默认使用 config 中的配置
        temperature: 温度参数
        max_tokens: 最大输出 token 数
        streaming: 是否启用流式输出

    Returns:
        ChatOpenAI 实例（OpenAI 兼容接口）
    """
    return ChatOpenAI(
        model=model or settings.model_writer,
        openai_api_key=settings.llm_api_key,
        openai_api_base=settings.llm_base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=streaming,
    )


def get_agent_llm(agent_type: str, streaming: bool = False) -> ChatOpenAI:
    """
    根据 Agent 类型获取对应的 LLM 实例

    Args:
        agent_type: Agent 类型 (planner/writer/consistency/reviewer/rewrite/context)
        streaming: 是否启用流式

    Returns:
        ChatOpenAI 实例
    """
    model_map = {
        "planner": settings.model_planner,
        "writer": settings.model_writer,
        "consistency": settings.model_consistency,
        "reviewer": settings.model_reviewer,
        "rewrite": settings.model_rewrite,
        "context": settings.model_context,
    }

    model_id = model_map.get(agent_type, settings.model_writer)

    # 不同任务使用不同温度
    temp_map = {
        "planner": 0.5,
        "writer": 0.8,
        "consistency": 0.1,
        "reviewer": 0.3,
        "rewrite": 0.7,
        "context": 0.1,
    }

    logger.debug(f"Creating LLM for agent={agent_type}, model={model_id}")

    return ChatOpenAI(
        model=model_id,
        openai_api_key=settings.llm_api_key,
        openai_api_base=settings.llm_base_url,
        temperature=temp_map.get(agent_type, 0.7),
        max_tokens=8192,  # 推理模型需要更多 token（reasoning + answer）
        streaming=streaming,
    )
