"""Context Agent - 历史章节加载、人物状态提取、世界观加载、时间线构建

接入 MemoryManager 获取真实记忆数据。
"""

from typing import Any

from loguru import logger

from src.memory.manager import memory_manager


async def context_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Context Agent 节点

    职责：
    1. 从 MemoryManager 加载四层记忆
    2. 组装上下文供下游 Agent 使用

    输入: story_id
    输出: novel_context (timeline, characters, foreshadows, world_state)
    """
    story_id = state.get("story_id", "")
    logger.info(f"[Context Agent] Loading context for story={story_id}")

    # 从记忆管理器组装上下文
    context = await memory_manager.assemble_context(
        story_id=story_id,
        recent_chapters=5,
    )

    event_count = len(context.get("timeline", []))
    char_count = len(context.get("characters", {}))
    fs_count = len(context.get("foreshadows", []))

    logger.info(
        f"[Context Agent] Context loaded: "
        f"{event_count} events, {char_count} characters, {fs_count} foreshadows"
    )

    return {
        "novel_context": context,
        "current_node": "novel_context",
        "execution_history": state.get("execution_history", []) + ["novel_context"],
    }
