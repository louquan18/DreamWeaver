"""Draft generation from Java-supplied confirmed writing context."""

import json
from collections.abc import AsyncIterator
from typing import Any

from src.models.llm_client import llm_stream_with_fallback
from src.models.provider import agent_model_chain, agent_temperature

DRAFT_SYSTEM_PROMPT = """你是 DreamWeaver 的正文写作 Agent。

你必须严格遵守 Java 传入的已确认小说蓝图和已确认章节中纲。
不得重新规划章节主线，不得改写已确认中纲的关键剧情、核心冲突、场景顺序、结尾钩子或已锁定事实。
可以在不改变关键剧情的前提下补充细节、环境描写、动作、心理和对话。
直接输出正文，不要输出标题、JSON、解释、提纲或作者注。
"""

DRAFT_HUMAN_PROMPT = """写作上下文如下：

【小说】
{story}

【已确认小说蓝图】
{blueprint}

【目标章节】
{chapter}

【已确认章节中纲】
{confirmed_outline}

【最近章节】
{recent_chapters}

【作者额外提示】
{extra_prompt}

【目标字数】
{target_words}

请基于以上信息写出完整章节正文。"""


def build_confirmed_outline_draft_messages(request: dict[str, Any]) -> list[dict[str, str]]:
    """Build the writer messages used by the internal Java-to-Python draft stream."""
    return [
        {"role": "system", "content": DRAFT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": DRAFT_HUMAN_PROMPT.format(
                story=_json(request.get("story")),
                blueprint=_json(request.get("blueprint")),
                chapter=_json(request.get("chapter")),
                confirmed_outline=_json(request.get("confirmedOutline")),
                recent_chapters=_json(request.get("recentChapters")),
                extra_prompt=request.get("extraPrompt") or "无",
                target_words=request.get("targetWords") or "按章节节奏自然完成",
            ),
        },
    ]


async def stream_confirmed_outline_draft(request: dict[str, Any]) -> AsyncIterator[str]:
    """Stream draft tokens using the confirmed outline as the hard writing plan."""
    messages = build_confirmed_outline_draft_messages(request)
    models = agent_model_chain("writer")
    temperature = agent_temperature("writer")
    async for token in llm_stream_with_fallback(messages, models=models, temperature=temperature):
        yield token


def _json(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, indent=2, sort_keys=True)
