"""Writer Agent - 根据规划生成章节草稿（流式输出）"""

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from src.models.provider import get_agent_llm

WRITER_SYSTEM_PROMPT = """你是一位优秀的网络小说作家，擅长写出引人入胜的长篇章节。

写作要求：
1. 严格按照章节大纲写作，不偏离核心目标和冲突
2. 保持人物性格一致，对话符合角色特征
3. 文笔流畅，节奏感强，适当使用环境描写和心理描写
4. 章节末尾留悬念，吸引读者继续阅读
5. 字数要求：3000-5000 字
6. 直接输出正文内容，不要输出标题、作者注等元信息

风格参考：
- 叙事为主，对话为辅
- 关键场景细写，过渡场景略写
- 人物内心活动丰富
- 战斗/冲突场景要有画面感
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


async def writer_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Writer Agent 节点

    职责：
    1. 根据大纲生成章节内容
    2. 保持文风和人物一致性
    3. 输出完整章节草稿
    """
    outline = state.get("chapter_outline", {})
    context = state.get("novel_context", {})

    logger.info("[Writer Agent] Generating draft...")

    llm = get_agent_llm("writer", streaming=False)

    messages = [
        SystemMessage(content=WRITER_SYSTEM_PROMPT),
        HumanMessage(content=WRITER_HUMAN_PROMPT.format(
            outline=json.dumps(outline, ensure_ascii=False, indent=2),
            characters=json.dumps(context.get("characters", {}), ensure_ascii=False, indent=2),
            world_rules=json.dumps(context.get("world_state", {}), ensure_ascii=False, indent=2),
            foreshadows=json.dumps(context.get("foreshadows", []), ensure_ascii=False, indent=2),
        )),
    ]

    try:
        response = await llm.ainvoke(messages)
        draft = response.content.strip()
        word_count = len(draft)
        logger.info(f"[Writer Agent] Draft generated: {word_count} chars")
    except Exception as e:
        logger.error(f"[Writer Agent] Generation failed: {e}")
        draft = f"[生成失败: {e}]"

    return {
        "generated_draft": draft,
        "current_node": "generate_draft",
        "execution_history": state.get("execution_history", []) + ["generate_draft"],
    }
