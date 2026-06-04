"""Reviewer Agent - 评审语言质量、节奏控制、冲突强度"""

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from src.models.provider import get_agent_llm

REVIEWER_SYSTEM_PROMPT = """你是一位资深网络小说评论家，负责评审章节质量。

评审维度（每项 0-100 分）：
1. language_quality - 语言质量（文笔、用词、句式）
2. rhythm_control - 节奏控制（张弛有度、不拖沓）
3. conflict_intensity - 冲突强度（悬念、矛盾、吸引力）
4. character_vividness - 人物刻画（生动、立体、有辨识度）
5. readability - 可读性（流畅度、阅读体验）

总分 = 各项加权平均（权重均为 20%）

输出格式（JSON）：
{
  "score": 85,
  "language_quality": 80,
  "rhythm_control": 85,
  "conflict_intensity": 90,
  "character_vividness": 80,
  "readability": 90,
  "strengths": ["优点1", "优点2"],
  "suggestions": [
    {"type": "language/rhythm/conflict/character", "detail": "具体建议", "priority": "high/medium/low"}
  ],
  "summary": "总体评价（一句话）"
}
"""

REVIEWER_HUMAN_PROMPT = """章节草稿：
{draft}

请对以上章节进行质量评审。"""


async def reviewer_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Reviewer Agent 节点

    职责：
    1. 评估语言质量
    2. 评估节奏控制
    3. 评估冲突强度
    4. 给出修改建议
    """
    draft = state.get("generated_draft", "")

    logger.info("[Reviewer Agent] Reviewing draft...")

    llm = get_agent_llm("reviewer")

    messages = [
        SystemMessage(content=REVIEWER_SYSTEM_PROMPT),
        HumanMessage(content=REVIEWER_HUMAN_PROMPT.format(draft=draft[:6000])),
    ]

    try:
        response = await llm.ainvoke(messages)
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        report = json.loads(content.strip())
        score = report.get("score", 0)
        logger.info(f"[Reviewer Agent] Score: {score}/100")
    except Exception as e:
        logger.warning(f"[Reviewer Agent] Failed to parse output: {e}")
        report = {
            "score": 0,
            "suggestions": [],
            "summary": f"评审失败: {e}",
        }

    return {
        "review_report": report,
        "current_node": "review",
        "execution_history": state.get("execution_history", []) + ["review"],
    }
