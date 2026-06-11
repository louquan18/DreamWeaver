"""上下文压缩流水线

从原始章节中提取结构化信息：
  原始章节 (3000字) → 事件抽取 + 人物变化 + 摘要 → 结构化存储 (~1000字)
  目标压缩率: 40%+
"""

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from src.models.provider import get_agent_llm

from .schema import CompressionResult, TimelineEvent

# ========== Prompts ==========

EXTRACT_EVENTS_PROMPT = """你是一位小说分析专家。从以下章节内容中提取关键事件。

输出 JSON 数组，每个事件包含：
- chapter: 章节号
- event: 事件描述（一句话）
- characters: 涉及的人物列表
- importance: high/medium/low
- is_permanent: true/false（是否永久保留在上下文中）

is_permanent=true 适用于：
- 主角获得核心能力/装备/灵根
- 世界观关键规则首次出现
- 重大转折点（背叛、死亡、重生、师徒结缘等）
- 影响全局的决策或发现

⚠️ 严格遵守以下格式：

```json
[
  {{
    "chapter": 1,
    "event": "林默在命运神碑上显现为灾星，被青石镇驱逐",
    "characters": ["林默", "王铁山", "镇长"],
    "importance": "high",
    "is_permanent": true
  }},
  {{
    "chapter": 1,
    "event": "王铁山偷偷给了林默一块黑色金属残片",
    "characters": ["林默", "王铁山"],
    "importance": "medium",
    "is_permanent": true
  }}
]
```

只提取对剧情有推动作用的事件（3-8 条），忽略日常描写。

章节号: {chapter_number}
章节内容:
{content}

输出纯 JSON 数组，不要其他文字。"""

EXTRACT_CHARACTERS_PROMPT = """你是一位小说分析专家。从以下章节内容中提取人物状态变化。

输出 JSON 对象，key 为人物名，value 包含：
- state_changes: 仅输出本章发生变化的字段（未变化的不要输出）：
    - cultivation_level: 新的修炼境界（如 "炼气四层"）
    - spirit_root: 灵根变化
    - location: 新位置
    - health_status: 健康状态变化
    - special_abilities_added: 新获得的能力列表 ["能力1", "能力2"]
    - equipment_added: 新获得的装备列表 ["装备1", "装备2"]
- new_relationships: 新建立的关系列表，每个关系是一个对象，包含 target、type、closeness 三个字段

⚠️ 严格遵守以下格式，不要用其他字段名：

```json
{{
  "林默": {{
    "state_changes": {{
      "cultivation_level": "炼气四层",
      "location": "天元城",
      "special_abilities_added": ["火球术"]
    }},
    "new_relationships": [
      {{"target": "李长老", "type": "师徒", "closeness": 60}},
      {{"target": "王铁山", "type": "父子", "closeness": 90}}
    ]
  }},
  "李长老": {{
    "state_changes": {{
      "location": "天元城"
    }},
    "new_relationships": []
  }}
}}
```

只提取本章中发生变化的信息。如果某个人物没有变化，不要包含在输出中。

章节内容:
{content}

输出纯 JSON 对象，不要其他文字。"""

GENERATE_SUMMARY_PROMPT = """你是一位小说分析专家。为以下章节生成简洁摘要。

要求：
- 100-200 字
- 包含主要事件和人物
- 保留关键细节，省略描写性文字
- 为后续章节创作提供足够上下文

章节内容:
{content}

输出纯文本摘要。"""


async def extract_events(
    content: str,
    chapter_number: int = 0,
) -> list[TimelineEvent]:
    """
    从章节内容中提取关键事件

    Args:
        content: 章节原文
        chapter_number: 章节号

    Returns:
        TimelineEvent 列表
    """
    llm = get_agent_llm("context")

    messages = [
        HumanMessage(content=EXTRACT_EVENTS_PROMPT.format(
            chapter_number=chapter_number,
            content=content[:4000],
        )),
    ]

    try:
        response = await llm.ainvoke(messages)
        raw = response.content
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]

        events_data = json.loads(raw.strip())
        events = [TimelineEvent(**e) for e in events_data]
        logger.info(f"[Compression] Extracted {len(events)} events from chapter {chapter_number}")
        return events
    except Exception as e:
        logger.warning(f"[Compression] Event extraction failed: {e}")
        return []


async def extract_character_changes(
    content: str,
) -> dict[str, dict[str, Any]]:
    """
    从章节内容中提取人物状态变化

    Returns:
        {character_name: {state_changes: {...}, new_relationships: [...]}}
    """
    llm = get_agent_llm("context")

    messages = [
        HumanMessage(content=EXTRACT_CHARACTERS_PROMPT.format(
            content=content[:4000],
        )),
    ]

    try:
        response = await llm.ainvoke(messages)
        raw = response.content
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]

        changes = json.loads(raw.strip())
        logger.info(f"[Compression] Extracted changes for {len(changes)} characters")
        return changes
    except Exception as e:
        logger.warning(f"[Compression] Character extraction failed: {e}")
        return {}


async def generate_summary(content: str) -> str:
    """
    生成章节摘要

    Args:
        content: 章节原文

    Returns:
        100-200 字摘要
    """
    llm = get_agent_llm("context")

    messages = [
        HumanMessage(content=GENERATE_SUMMARY_PROMPT.format(
            content=content[:4000],
        )),
    ]

    try:
        response = await llm.ainvoke(messages)
        summary = response.content.strip()
        logger.info(f"[Compression] Summary generated: {len(summary)} chars")
        return summary
    except Exception as e:
        logger.warning(f"[Compression] Summary generation failed: {e}")
        return f"[摘要生成失败: {e}]"


async def compress_chapter(
    content: str,
    chapter_number: int = 0,
    story_id: str = "",
    chapter_db_id: str = "",
) -> CompressionResult:
    """
    章节压缩流水线

    流程:
      原始章节 → 事件抽取 + 人物变化 + 摘要生成 → 结构化存储 + 向量索引

    Args:
        content: 章节原文
        chapter_number: 章节号
        story_id: 小说 ID（用于向量索引）
        chapter_db_id: 章节 DB 主键（用于原文引用）

    Returns:
        CompressionResult 包含压缩后的结构化数据
    """
    import asyncio

    logger.info(f"[Compression] Compressing chapter {chapter_number} ({len(content)} chars)")

    # 并行执行三个提取任务
    events_task = extract_events(content, chapter_number)
    characters_task = extract_character_changes(content)
    summary_task = generate_summary(content)

    events, character_changes, summary = await asyncio.gather(
        events_task,
        characters_task,
        summary_task,
    )

    # 计算压缩后大小
    compressed_size = len(summary) + len(json.dumps(
        {"events": [e.model_dump() for e in events], "characters": character_changes},
        ensure_ascii=False,
    ))

    result = CompressionResult(
        summary=summary,
        events=events,
        character_changes=character_changes,
        original_length=len(content),
        compressed_length=compressed_size,
        original_chapter_ref=chapter_db_id,
    )
    result.calculate_rate()

    # 保存摘要到 Chroma 向量库
    if story_id and summary:
        from .vector_store import add_chapter_summary

        await add_chapter_summary(
            story_id=story_id,
            chapter_number=chapter_number,
            summary=summary,
            metadata={"compression_rate": result.compression_rate},
        )

    # 保存原文分段 embedding（支持深度语义检索）
    if story_id and content:
        from .vector_store import add_chapter_fulltext

        await add_chapter_fulltext(
            story_id=story_id,
            chapter_number=chapter_number,
            content=content,
        )

    logger.info(
        f"[Compression] Done: {len(content)} → {compressed_size} chars "
        f"(rate: {result.compression_rate:.1%})"
    )

    return result
