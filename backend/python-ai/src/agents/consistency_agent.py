"""Consistency Agent - 检测人物/世界观/情节一致性

使用 consistency_rules.py 中定义的详细规则库。
"""

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from src.models.provider import get_agent_llm

from .consistency_rules import build_rule_check_prompt

CONSISTENCY_SYSTEM_PROMPT = """你是一位严谨的小说校对编辑，专门检查长篇小说的一致性问题。

你需要按照以下规则逐条检查，输出结构化的检查报告。

{rules}

输出格式（严格 JSON）：
{{
  "character_issues": [
    {{
      "rule_id": "C01",
      "severity": "high/medium/low",
      "description": "问题描述",
      "location": "大致位置（如：第X段/对话/描写）",
      "suggestion": "修复建议"
    }}
  ],
  "world_issues": [
    {{
      "rule_id": "W01",
      "severity": "high/medium/low",
      "description": "...",
      "location": "...",
      "suggestion": "..."
    }}
  ],
  "plot_issues": [
    {{
      "rule_id": "P01",
      "severity": "high/medium/low",
      "description": "...",
      "location": "...",
      "suggestion": "..."
    }}
  ],
  "total_issues": 0,
  "high_issues": 0,
  "summary": "总体评价（一句话）"
}}

注意：
- 只报告确实存在的问题，不要猜测
- 如果没有发现问题，返回空数组
- total_issues = character_issues.length + world_issues.length + plot_issues.length
- high_issues = severity 为 high 的问题总数
"""

CONSISTENCY_HUMAN_PROMPT = """章节草稿：
{draft}

人物设定：
{characters}

世界观规则：
{world_rules}

时间线：
{timeline}

活跃伏笔：
{foreshadows}

请逐条检查以上草稿的一致性问题。"""


async def consistency_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Consistency Agent 节点

    职责：
    1. 人物一致性检测（性格、能力、关系、称谓、生死）
    2. 世界观一致性检测（规则、设定、地理）
    3. 情节一致性检测（伏笔、因果、连贯性、自洽）
    """
    draft = state.get("generated_draft", "")
    context = state.get("novel_context", {})

    logger.info("[Consistency Agent] Checking consistency with detailed rules...")

    llm = get_agent_llm("consistency")

    # 构建规则 prompt
    rules_prompt = build_rule_check_prompt()

    messages = [
        SystemMessage(content=CONSISTENCY_SYSTEM_PROMPT.format(rules=rules_prompt)),
        HumanMessage(content=CONSISTENCY_HUMAN_PROMPT.format(
            draft=draft[:6000],
            characters=json.dumps(context.get("characters", {}), ensure_ascii=False, indent=2),
            world_rules=json.dumps(context.get("world_state", {}), ensure_ascii=False, indent=2),
            timeline=json.dumps(context.get("timeline", []), ensure_ascii=False, indent=2),
            foreshadows=json.dumps(context.get("foreshadows", []), ensure_ascii=False, indent=2),
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

        # 确保总数正确
        char_count = len(report.get("character_issues", []))
        world_count = len(report.get("world_issues", []))
        plot_count = len(report.get("plot_issues", []))
        report["total_issues"] = char_count + world_count + plot_count

        # 计算 high 级别问题数
        all_issues = (
            report.get("character_issues", [])
            + report.get("world_issues", [])
            + report.get("plot_issues", [])
        )
        report["high_issues"] = sum(
            1 for i in all_issues if i.get("severity") == "high"
        )

        logger.info(
            f"[Consistency Agent] Found {report['total_issues']} issues "
            f"({report['high_issues']} high)"
        )
    except Exception as e:
        logger.warning(f"[Consistency Agent] Failed to parse output: {e}")
        report = {
            "character_issues": [],
            "world_issues": [],
            "plot_issues": [],
            "total_issues": 0,
            "high_issues": 0,
            "summary": f"检查失败: {e}",
        }

    return {
        "consistency_report": report,
        "current_node": "check_consistency",
        "execution_history": state.get("execution_history", []) + ["check_consistency"],
    }
