"""工作流节点封装"""

from typing import Any

from loguru import logger

from src.agents import (
    consistency_agent_node,
    context_agent_node,
    planner_agent_node,
    reviewer_agent_node,
    rewrite_agent_node,
    writer_agent_node,
)
from src.core.database import async_session_factory
from src.memory.manager import memory_manager
from src.repositories.memory_repository import MemoryRepository


async def load_runtime_context_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    加载运行时上下文节点

    职责：
    - 注入 MemoryRepository 到 MemoryManager（启用 DB 持久化）
    - 验证输入参数
    """
    story_id = state.get("story_id", "")
    logger.info(f"[Runtime] Loading context for story={story_id}")

    # 注入 DB Repository 到 MemoryManager
    try:
        session = async_session_factory()
        repo = MemoryRepository(session)
        memory_manager.set_repository(repo)
        logger.info("[Runtime] MemoryRepository injected")
    except Exception as e:
        logger.warning(f"[Runtime] DB injection failed, using in-memory: {e}")

    return {
        "current_node": "load_runtime_context",
        "execution_history": state.get("execution_history", []) + ["load_runtime_context"],
        "metadata": {
            **state.get("metadata", {}),
            "initialized": True,
        },
    }


async def commit_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    提交节点 - 工作流最终步骤

    职责：
    1. 运行压缩流水线（事件抽取 + 人物变化 + 摘要）
    2. 将提取的结构化记忆持久化到 DB
    3. 记录最终统计
    """
    story_id = state.get("story_id", "")
    chapter_id = state.get("chapter_id", "")
    draft = state.get("generated_draft", "")
    word_count = len(draft)

    logger.info(f"[Commit] Chapter committed. Word count: {word_count}")

    if not draft or word_count < 100:
        logger.warning("[Commit] Draft too short, skipping compression")
        return {
            "current_node": "commit",
            "execution_history": state.get("execution_history", []) + ["commit"],
            "metadata": {**state.get("metadata", {}), "final_word_count": word_count, "status": "completed"},
        }

    # ── 运行压缩流水线 ──
    try:
        from src.memory.compression import compress_chapter
        from src.memory.schema import TimelineEvent, CharacterState, Foreshadow

        # 从 chapter_id 提取章节号（如果格式是 "ch-N"）
        chapter_num = 0
        try:
            if "ch" in chapter_id:
                chapter_num = int(chapter_id.split("-")[-1])
        except (ValueError, IndexError):
            pass

        logger.info("[Commit] Running compression pipeline...")
        result = await compress_chapter(draft, chapter_number=chapter_num, story_id=story_id)

        # ── 保存时间线事件 ──
        for event in result.events:
            await memory_manager.add_event(story_id, event)
        logger.info(f"[Commit] Saved {len(result.events)} timeline events")

        # ── 保存人物状态变化 ──
        for char_name, changes in result.character_changes.items():
            try:
                if not isinstance(changes, dict):
                    continue
                state_changes = changes.get("state_changes", {})
                if isinstance(state_changes, dict):
                    await memory_manager.update_character(
                        story_id, char_name, state_changes, chapter=chapter_num
                    )
                # 保存新人物关系
                new_rels = changes.get("new_relationships", [])
                if isinstance(new_rels, list):
                    for rel in new_rels:
                        try:
                            if isinstance(rel, dict):
                                target = str(rel.get("target") or rel.get("name") or rel.get("character") or "unknown")
                                rel_type = str(rel.get("type") or rel.get("relationship") or rel.get("relation") or "unknown")
                                closeness = rel.get("closeness") or rel.get("intimacy") or rel.get("level") or 0
                                if isinstance(closeness, str):
                                    closeness = 0
                                await memory_manager.add_relationship(
                                    story_id, char_name, target, rel_type, closeness=int(closeness),
                                )
                            elif isinstance(rel, (list, tuple)) and len(rel) >= 2:
                                # 兼容 LLM 返回列表格式 [target, type, closeness]
                                await memory_manager.add_relationship(
                                    story_id, char_name, str(rel[0]), str(rel[1]),
                                    closeness=int(rel[2]) if len(rel) > 2 and isinstance(rel[2], (int, float)) else 0,
                                )
                        except Exception as re:
                            logger.debug(f"[Commit] Skip relationship for {char_name}: {re}")
            except Exception as e:
                logger.debug(f"[Commit] Skip character {char_name}: {e}")
        logger.info(f"[Commit] Updated {len(result.character_changes)} characters")

        # ── 保存摘要事件 ──
        if result.summary:
            summary_event = TimelineEvent(
                chapter=chapter_num,
                event=f"[摘要] {result.summary}",
                importance="medium",
            )
            await memory_manager.add_event(story_id, summary_event)

        # ── 更新世界状态（如果有变化）──
        # 从大纲中提取可能的世界观变化
        outline = state.get("chapter_outline", {})
        if outline.get("foreshadow_updates"):
            for fs_update in outline["foreshadow_updates"]:
                if fs_update.get("action") == "plant":
                    from src.memory.schema import Foreshadow
                    import uuid
                    fs = Foreshadow(
                        id=f"fs-{uuid.uuid4().hex[:8]}",
                        chapter_planted=chapter_num,
                        content=fs_update.get("detail", ""),
                        status="active",
                    )
                    await memory_manager.add_foreshadow(story_id, fs)

        logger.info(
            f"[Commit] Compression done: {result.original_length} → {result.compressed_length} chars "
            f"(rate: {result.compression_rate:.1%})"
        )

    except Exception as e:
        import traceback
        logger.warning(f"[Commit] Compression pipeline failed: {e}")
        logger.debug(f"[Commit] Traceback: {traceback.format_exc()}")

    return {
        "current_node": "commit",
        "execution_history": state.get("execution_history", []) + ["commit"],
        "metadata": {
            **state.get("metadata", {}),
            "final_word_count": word_count,
            "status": "completed",
        },
    }


# Re-export agent nodes
__all__ = [
    "load_runtime_context_node",
    "context_agent_node",
    "planner_agent_node",
    "writer_agent_node",
    "consistency_agent_node",
    "reviewer_agent_node",
    "rewrite_agent_node",
    "commit_node",
]
