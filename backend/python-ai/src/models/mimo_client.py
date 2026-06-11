"""小米 MiMo API 客户端 - 原生支持 reasoning_content 流式"""

import json
import httpx
from typing import AsyncIterator

from loguru import logger
from src.core.config import settings


async def mimo_stream(
    messages: list[dict],
    model: str = "mimo-v2.5-pro",
    max_tokens: int = 8192,
    temperature: float = 0.7,
) -> AsyncIterator[str]:
    """
    MiMo 流式调用 - 逐 token yield content

    处理 MiMo 特有的 reasoning_content 字段：
    - reasoning_content: 模型思考过程（不 yield）
    - content: 最终输出（yield 给调用方）
    """
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }

    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=300) as client:
        async with client.stream(
            "POST",
            f"{settings.llm_base_url}/chat/completions",
            headers=headers,
            json=body,
        ) as response:
            chunk_count = 0
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    logger.debug(f"[MiMo] Stream finished, {chunk_count} chunks")
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


async def mimo_invoke(
    messages: list[dict],
    model: str = "mimo-v2.5-pro",
    max_tokens: int = 8192,
    temperature: float = 0.7,
) -> str:
    """
    MiMo 非流式调用 - 返回完整 content
    """
    full_content = ""
    async for chunk in mimo_stream(messages, model, max_tokens, temperature):
        full_content += chunk
    return full_content
