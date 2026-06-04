"""Consistency Agent - 检测人物/世界观/情节一致性"""

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from src.models.provider import get_agent_llm

CONSISTENCY_SYSTEM_PROMPT = """你是一位严谨的小说校对编辑，专门检查长篇小说的一致性问题。

你需要检查以下三个维度：

1. 人物一致性
   - 性格是否与设定一致
   - 能力是否超出已知范围
   - 人物关系是否正确
   - 称谓是否一致

2. 世界观一致性
   - 是否违反已建立的世界规则
   - 力量体系是否自洽
   - 地理/历史设定是否矛盾

3. 情节一致性
   - 是否有因果缺失
   - 是否有伏笔遗失
   - 是否有时间线矛盾
   - 是否有剧情跳跃

输出格式（JSON）：
{
  "character_issues": [
    {"severity": "high/medium/low", "description": "问题描述", "location": "大致位置"}
  ],
  "world_issues": [...],
  "plot_issues": [...],
  "total_issues": 0,
  "summary": "总体评价"
}
"""

CONSISTENCY_HUMAN_PROMPT = """章节草稿：
{draft}

人物设定：
{characters}

世界观规则：
{world_rules}

时间线：
{timeline}

请检查以上草稿的一致性问题。"""


async def consistency_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Consistency Agent 节点

    职责：
    1. 人物一致性检测（性格、能力、关系）
    2. 世界观一致性检测（规则、设定）
    3. 情节一致性检测（伏笔、因果、时间线）
    """
    draft = state.get("generated_draft", "")
    context = state.get("novel_context", {})

    logger.info("[Consistency Agent] Checking consistency...")

    llm = get_agent_llm("consistency")

    messages = [
        SystemMessage(content=CONSISTENCY_SYSTEM_PROMPT),
        HumanMessage(content=CONSISTENCY_HUMAN_PROMPT.format(
            draft=draft[:6000],  # 截断避免超长
            characters=json.dumps(context.get("characters", {}), ensure_ascii=False, indent=2),
            world_rules=json.dumps(context.get("world_state", {}), ensure_ascii=False, indent=2),
            timeline=json.dumps(context.get("timeline", []), ensure_ascii=False, indent=2),
        )),
    ]

    try:
        response = await llm.ainvoke(messages)
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        report = json.loads(content.strip())
        total = report.get("total_issues", 0)
        # 如果 LLM 没有计算总数，手动计算
        if total == 0:
            total = (
                len(report.get("character_issues", []))
                + len(report.get("world_issues", []))
                + len(report.get("plot_issues", []))
            )
            report["total_issues"] = total

        logger.info(f"[Consistency Agent] Found {total} issues")
    except Exception as e:
        logger.warning(f"[Consistency Agent] Failed to parse output: {e}")
        report = {
            "character_issues": [],
            "world_issues": [],
            "plot_issues": [],
            "total_issues": 0,
            "summary": f"检查失败: {e}",
        }

    return {
        "consistency_report": report,
        "current_node": "check_consistency",
        "execution_history": state.get("execution_history", []) + ["check_consistency"],
    }
