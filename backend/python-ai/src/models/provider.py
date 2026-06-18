"""LLM Provider 抽象层

统一封装 OpenAI 兼容接口，默认对接 OpenRouter 多模型聚合
（一个 API Key 调度 Claude / GPT / DeepSeek / Qwen 等）。
也可通过 llm_base_url 指向其他兼容网关或本地部署。
"""

from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from loguru import logger

from src.core.config import settings

# 各 Agent 的主模型 / fallback 备用模型（取自配置，env 可覆盖）
_AGENT_PRIMARY = {
    "planner": lambda: settings.model_planner,
    "writer": lambda: settings.model_writer,
    "consistency": lambda: settings.model_consistency,
    "reviewer": lambda: settings.model_reviewer,
    "rewrite": lambda: settings.model_rewrite,
    "context": lambda: settings.model_context,
}
_AGENT_FALLBACK = {
    "planner": lambda: settings.model_planner_fallback,
    "writer": lambda: settings.model_writer_fallback,
    "consistency": lambda: settings.model_consistency_fallback,
    "reviewer": lambda: settings.model_reviewer_fallback,
    "rewrite": lambda: settings.model_rewrite_fallback,
    "context": lambda: settings.model_context_fallback,
}
# 不同任务使用不同温度
_AGENT_TEMPERATURE = {
    "planner": 0.5,
    "writer": 0.8,
    "consistency": 0.1,
    "reviewer": 0.3,
    "rewrite": 0.7,
    "context": 0.1,
}


def openrouter_headers() -> dict[str, str]:
    """OpenRouter 推荐请求头（用量归因，可留空）"""
    headers: dict[str, str] = {}
    if settings.openrouter_referer:
        headers["HTTP-Referer"] = settings.openrouter_referer
    if settings.openrouter_title:
        headers["X-Title"] = settings.openrouter_title
    return headers


def agent_model_chain(agent_type: str) -> list[str]:
    """返回某 Agent 的模型调用链 [主模型, 备用模型?]（去空、去重）"""
    primary = _AGENT_PRIMARY.get(agent_type, lambda: settings.model_writer)()
    fallback = _AGENT_FALLBACK.get(agent_type, lambda: "")()
    chain = [primary]
    if fallback and fallback != primary:
        chain.append(fallback)
    return chain


def agent_temperature(agent_type: str) -> float:
    return _AGENT_TEMPERATURE.get(agent_type, 0.7)


def _build_chat(model: str, temperature: float, streaming: bool) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        openai_api_key=settings.llm_api_key,
        openai_api_base=settings.llm_base_url,
        temperature=temperature,
        max_tokens=8192,  # 推理模型需要更多 token（reasoning + answer）
        streaming=streaming,
        default_headers=openrouter_headers() or None,
    )


def get_llm(
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    streaming: bool = False,
) -> ChatOpenAI:
    """获取一个 LLM 实例（不带 fallback），默认使用 writer 模型"""
    return ChatOpenAI(
        model=model or settings.model_writer,
        openai_api_key=settings.llm_api_key,
        openai_api_base=settings.llm_base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=streaming,
        default_headers=openrouter_headers() or None,
    )


def get_agent_llm(agent_type: str, streaming: bool = False) -> Runnable:
    """
    根据 Agent 类型获取 LLM（主模型 + fallback 备用模型）

    主模型调用失败时，LangChain 自动切换到备用模型。
    返回 Runnable，调用方按 `.ainvoke(messages)` 使用即可。
    """
    chain = agent_model_chain(agent_type)
    temperature = agent_temperature(agent_type)

    primary = _build_chat(chain[0], temperature, streaming)
    if len(chain) > 1:
        fallbacks = [_build_chat(m, temperature, streaming) for m in chain[1:]]
        logger.debug(
            f"Agent={agent_type} primary={chain[0]} fallback={chain[1:]}"
        )
        return primary.with_fallbacks(fallbacks)

    logger.debug(f"Agent={agent_type} model={chain[0]} (no fallback)")
    return primary
