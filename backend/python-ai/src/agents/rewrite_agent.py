"""Rewrite Agent - 根据评审结果定位问题、局部修复、重写优化"""

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from src.models.provider import get_agent_llm

REWRITE_SYSTEM_PROMPT = """你是一位网络小说修改专家，负责根据评审意见优化章节。

修改原则：
1. 只针对评审指出的问题进行修改，不要大幅改动没有问题的部分
2. 保持整体风格和叙事连贯性
3. 优先处理高优先级（high）问题
4. 修改后字数保持在原文字数的 80%-120% 之间
5. 直接输出修改后的完整章节内容，不要输出修改说明

注意事项：
- 如果评审建议不合理，可以忽略
- 保持人物对话的自然感
- 不要改变核心剧情走向
"""

REWRITE_HUMAN_PROMPT = """原始草稿：
{draft}

评审报告：
{review_report}

请根据评审意见修改以上草稿，输出完整的修改后内容。"""


async def rewrite_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Rewrite Agent 节点

    职责：
    1. 分析评审报告中的问题
    2. 定位问题段落
    3. 局部重写修复
    4. 保持整体连贯性
    """
    draft = state.get("generated_draft", "")
    review_report = state.get("review_report", {})
    retry_count = state.get("retry_count", 0)

    logger.info(f"[Rewrite Agent] Rewriting (attempt {retry_count + 1})...")

    llm = get_agent_llm("rewrite")

    messages = [
        SystemMessage(content=REWRITE_SYSTEM_PROMPT),
        HumanMessage(content=REWRITE_HUMAN_PROMPT.format(
            draft=draft,
            review_report=json.dumps(review_report, ensure_ascii=False, indent=2),
        )),
    ]

    try:
        response = await llm.ainvoke(messages)
        new_draft = response.content.strip()
        logger.info(f"[Rewrite Agent] Rewrite complete: {len(new_draft)} chars")
    except Exception as e:
        logger.error(f"[Rewrite Agent] Rewrite failed: {e}")
        new_draft = draft  # 失败时保留原文

    return {
        "generated_draft": new_draft,
        "current_node": "rewrite",
        "retry_count": retry_count + 1,
        "execution_history": state.get("execution_history", []) + ["rewrite"],
    }
