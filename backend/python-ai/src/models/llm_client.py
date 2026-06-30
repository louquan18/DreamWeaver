"""通用 LLM 流式客户端（OpenAI 兼容 / OpenRouter）

直接走 HTTP SSE，逐 token yield，供 Writer Agent 做 token 级实时输出。
兼容推理模型：跳过 reasoning_content，只 yield 最终 content。
"""

import json
from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx
from loguru import logger

from src.core.config import settings
from src.models.provider import openrouter_headers


async def llm_stream(
    messages: list[dict],
    model: str,
    max_tokens: int = 8192,
    temperature: float = 0.7,
    extra_body: dict[str, Any] | None = None,
) -> AsyncIterator[str]:
    """
    流式调用指定模型 - 逐 token yield content

    - reasoning_content: 模型思考过程（不 yield）
    - content: 最终输出（yield 给调用方）
    """
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
        **openrouter_headers(),
    }

    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }
    if extra_body:
        body.update(extra_body)

    async with httpx.AsyncClient(timeout=300) as client:
        async with client.stream(
            "POST",
            f"{settings.llm_base_url}/chat/completions",
            headers=headers,
            json=body,
        ) as response:
            response.raise_for_status()
            chunk_count = 0
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    logger.debug(f"[LLM:{model}] Stream finished, {chunk_count} chunks")
                    break

                try:
                    data = json.loads(data_str)
                    delta = data["choices"][0]["delta"]
                    # 只 yield content，跳过 reasoning_content
                    content = delta.get("content")
                    if content:
                        chunk_count += 1
                        yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue


async def llm_stream_with_fallback(
    messages: list[dict],
    models: list[str],
    max_tokens: int = 8192,
    temperature: float = 0.7,
    model_extra_body: Callable[[str], dict[str, Any] | None] | None = None,
) -> AsyncIterator[str]:
    """
    依次尝试 models 中的模型做流式输出。

    仅当某模型在**尚未产出任何 token** 时报错，才切换到下一个备用模型；
    若已经流出部分 token 再报错，则直接抛出（避免下游收到重复内容）。
    """
    last_exc: Exception | None = None
    for idx, model in enumerate(models):
        emitted = False
        try:
            extra_body = model_extra_body(model) if model_extra_body else None
            if extra_body:
                stream = llm_stream(
                    messages,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    extra_body=extra_body,
                )
            else:
                stream = llm_stream(
                    messages,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            async for token in stream:
                emitted = True
                yield token
            if not emitted:
                last_exc = RuntimeError(f"[LLM:{model}] returned an empty response")
                if idx < len(models) - 1:
                    logger.warning(f"[LLM:{model}] returned no content, falling back to next")
                    continue
                logger.error(f"[LLM:{model}] returned no content and no fallback left")
                raise last_exc
            return  # 成功完成
        except Exception as e:  # noqa: BLE001 - 需捕获任意网络/模型异常以触发 fallback
            last_exc = e
            if emitted:
                logger.error(f"[LLM:{model}] failed after streaming started, not falling back: {e}")
                raise
            if idx < len(models) - 1:
                logger.warning(f"[LLM:{model}] failed before any token, falling back to next: {e}")
                continue
            logger.error(f"[LLM:{model}] failed and no fallback left: {e}")
    if last_exc is not None:
        raise last_exc


async def llm_invoke(
    messages: list[dict],
    model: str,
    max_tokens: int = 8192,
    temperature: float = 0.7,
) -> str:
    """非流式调用 - 返回完整 content"""
    full_content = ""
    async for chunk in llm_stream(messages, model, max_tokens, temperature):
        full_content += chunk
    return full_content
