"""Planner Agent - 章节规划、冲突设计、剧情推进"""

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from src.models.provider import get_agent_llm

PLANNER_SYSTEM_PROMPT = """你是一位资深网络小说策划编辑，擅长章节规划。

你的任务是根据小说上下文（人物状态、时间线、伏笔、世界观）规划下一章节。

输出格式（JSON）：
{
  "goal": "本章核心目标（一句话）",
  "conflict": "主要冲突描述",
  "plot_points": [
    "情节点1：...",
    "情节点2：...",
    "情节点3：..."
  ],
  "character_arcs": {
    "角色名": "本章角色发展"
  },
  "foreshadow_updates": [
    {"id": "伏笔ID", "action": "plant/advance/resolve", "detail": "..."}
  ],
  "estimated_words": 3000,
  "tone": "本章基调（紧张/温馨/悲壮等）"
}

要求：
- 推进主线剧情，不能原地踏步
- 至少有 1 个冲突或悬念
- 保持人物性格一致
- 如有活跃伏笔，考虑在合适时机推进或回收
"""

PLANNER_HUMAN_PROMPT = """小说上下文：
{context}

上一章内容摘要：
{last_chapter}

请规划下一章节（chapter_id: {chapter_id}）的大纲。"""


async def planner_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Planner Agent 节点

    职责：
    1. 分析剧情进度
    2. 设计章节冲突
    3. 规划关键情节点
    4. 安排伏笔推进
    """
    context = state.get("novel_context", {})
    chapter_id = state.get("chapter_id", "")

    logger.info(f"[Planner Agent] Planning chapter={chapter_id}")

    # 提取上一章摘要
    recent = context.get("recent_chapters", [])
    last_chapter = recent[-1] if recent else "（暂无历史章节，这是第一章）"

    # 调用 LLM 生成大纲
    llm = get_agent_llm("planner")

    messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        HumanMessage(content=PLANNER_HUMAN_PROMPT.format(
            context=json.dumps(context, ensure_ascii=False, indent=2),
            last_chapter=last_chapter,
            chapter_id=chapter_id,
        )),
    ]

    try:
        response = await llm.ainvoke(messages)
        # 尝试解析 JSON
        content = response.content
        # 提取 JSON 块
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        outline = json.loads(content.strip())
        logger.info(f"[Planner Agent] Outline generated: goal={outline.get('goal', '')[:50]}")
    except Exception as e:
        logger.warning(f"[Planner Agent] Failed to parse LLM output: {e}")
        # 使用默认大纲
        outline = {
            "goal": "推进剧情发展",
            "conflict": "待定",
            "plot_points": ["待定"],
            "estimated_words": 3000,
        }

    return {
        "chapter_outline": outline,
        "current_node": "plan_chapter",
        "execution_history": state.get("execution_history", []) + ["plan_chapter"],
    }
