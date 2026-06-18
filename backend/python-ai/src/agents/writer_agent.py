"""Writer Agent - Token 级流式输出（OpenRouter 多模型 + fallback）"""

import json
from typing import Any

from loguru import logger

from src.models.llm_client import llm_stream_with_fallback
from src.models.provider import agent_model_chain, agent_temperature
from src.workflows.token_buffer import push_done_sync, push_token_sync

WRITER_SYSTEM_PROMPT = """你是一位优秀的网络小说作家，擅长写出引人入胜的长篇章节。

写作要求：
1. 严格按照章节大纲写作，不偏离核心目标和冲突
2. 保持人物性格一致，对话符合角色特征
3. 文笔流畅，节奏感强，适当使用环境描写和心理描写
4. 章节末尾留悬念，吸引读者继续阅读
5. 字数要求：3000-5000 字
6. 直接输出正文内容，不要输出标题、作者注等元信息
"""

WRITER_HUMAN_PROMPT = """章节大纲：
{outline}

人物信息：
{characters}

世界观规则：
{world_rules}

活跃伏笔：
{foreshadows}

请根据以上信息撰写完整章节内容。"""


async def writer_agent_node(
    state: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Writer Agent 节点

    通过 OpenRouter（OpenAI 兼容流式）实现 token 级流式输出，主模型失败自动 fallback。
    每个 content token 实时推送到 token_buffer。
    """
    thread_id = _get_thread_id(state, config)
    outline = state.get("chapter_outline", {})
    context = state.get("novel_context", {})

    models = agent_model_chain("writer")
    temperature = agent_temperature("writer")
    logger.info(f"[Writer Agent] Streaming draft via {models} (thread={thread_id})")

    messages = [
        {"role": "system", "content": WRITER_SYSTEM_PROMPT},
        {"role": "user", "content": WRITER_HUMAN_PROMPT.format(
            outline=json.dumps(outline, ensure_ascii=False, indent=2),
            characters=json.dumps(context.get("characters", {}), ensure_ascii=False, indent=2),
            world_rules=json.dumps(context.get("world_state", {}), ensure_ascii=False, indent=2),
            foreshadows=json.dumps(context.get("foreshadows", []), ensure_ascii=False, indent=2),
        )},
    ]

    try:
        draft = ""
        token_count = 0
        async for token in llm_stream_with_fallback(messages, models=models, temperature=temperature):
            draft += token
            push_token_sync(thread_id, token)
            token_count += 1
            if token_count <= 3:
                logger.debug(f"[Writer Agent] Token {token_count}: {token[:30]}")

        push_done_sync(thread_id)
        logger.info(f"[Writer Agent] Draft generated: {len(draft)} chars, {token_count} tokens streamed")
    except Exception as e:
        logger.error(f"[Writer Agent] Generation failed: {e}")
        draft = f"[生成失败: {e}]"
        push_done_sync(thread_id)

    return {
        "generated_draft": draft,
        "current_node": "generate_draft",
        "execution_history": state.get("execution_history", []) + ["generate_draft"],
    }


def _get_thread_id(state: dict[str, Any], config: dict[str, Any] | None) -> str:
    # 最优先：SSE 端通过 state.metadata 显式下发的 buffer key（= generation_id）
    metadata = state.get("metadata") or {}
    sse_thread_id = metadata.get("sse_thread_id")
    if sse_thread_id:
        return str(sse_thread_id)

    # 兼容：LangGraph config 注入的 thread_id
    configured_thread_id = (config or {}).get("configurable", {}).get("thread_id")
    if configured_thread_id:
        return str(configured_thread_id)

    story_id = state.get("story_id", "")
    chapter_id = state.get("chapter_id", "")
    return f"{story_id}-{chapter_id}"
