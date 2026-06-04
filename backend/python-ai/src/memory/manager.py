"""Memory Manager - 统一记忆管理接口

负责四层记忆的 CRUD 操作和上下文组装。
当前使用内存存储，后续接入 PostgreSQL + Chroma。
"""

from typing import Any

from loguru import logger

from .schema import (
    CharacterState,
    Foreshadow,
    NovelMemory,
    Relationship,
    TimelineEvent,
    WorldState,
)


class MemoryManager:
    """
    小说记忆管理器

    管理 Timeline / Character Graph / Foreshadow / World State 四层记忆。
    每个 story_id 维护独立的记忆空间。
    """

    def __init__(self):
        # 内存存储 {story_id: NovelMemory}
        self._store: dict[str, NovelMemory] = {}

    def _get_or_create(self, story_id: str) -> NovelMemory:
        if story_id not in self._store:
            self._store[story_id] = NovelMemory()
        return self._store[story_id]

    # ========== Timeline ==========

    def add_event(self, story_id: str, event: TimelineEvent) -> None:
        """添加时间线事件"""
        memory = self._get_or_create(story_id)
        memory.timeline.append(event)
        logger.debug(f"[Memory] Added event to story={story_id}: {event.event[:50]}")

    def get_events(
        self,
        story_id: str,
        last_n: int | None = None,
        importance: str | None = None,
    ) -> list[TimelineEvent]:
        """获取时间线事件"""
        memory = self._get_or_create(story_id)
        events = memory.timeline

        if importance:
            events = [e for e in events if e.importance == importance]
        if last_n:
            events = events[-last_n:]

        return events

    # ========== Character Graph ==========

    def update_character(
        self,
        story_id: str,
        name: str,
        state_update: dict[str, Any] | None = None,
        chapter: int = 0,
    ) -> None:
        """更新人物状态"""
        memory = self._get_or_create(story_id)

        if name not in memory.characters:
            memory.characters[name] = CharacterState(name=name)

        char = memory.characters[name]
        if state_update:
            char.current_state.update(state_update)
        if chapter > 0:
            char.last_appeared = chapter

        logger.debug(f"[Memory] Updated character={name} in story={story_id}")

    def add_relationship(
        self,
        story_id: str,
        from_char: str,
        to_char: str,
        rel_type: str,
        closeness: int = 0,
    ) -> None:
        """添加人物关系"""
        memory = self._get_or_create(story_id)

        if from_char not in memory.characters:
            memory.characters[from_char] = CharacterState(name=from_char)

        memory.characters[from_char].relationships[to_char] = Relationship(
            type=rel_type,
            closeness=closeness,
        )

    def get_characters(self, story_id: str) -> dict[str, CharacterState]:
        """获取所有人物"""
        memory = self._get_or_create(story_id)
        return memory.characters

    def get_character(self, story_id: str, name: str) -> CharacterState | None:
        """获取单个人物"""
        memory = self._get_or_create(story_id)
        return memory.characters.get(name)

    # ========== Foreshadow ==========

    def add_foreshadow(self, story_id: str, foreshadow: Foreshadow) -> None:
        """添加伏笔"""
        memory = self._get_or_create(story_id)
        memory.foreshadows.append(foreshadow)
        logger.debug(f"[Memory] Added foreshadow={foreshadow.id} to story={story_id}")

    def resolve_foreshadow(self, story_id: str, foreshadow_id: str) -> bool:
        """回收伏笔"""
        memory = self._get_or_create(story_id)
        for fs in memory.foreshadows:
            if fs.id == foreshadow_id and fs.status == "active":
                fs.status = "resolved"
                logger.debug(f"[Memory] Resolved foreshadow={foreshadow_id}")
                return True
        return False

    def get_active_foreshadows(self, story_id: str) -> list[Foreshadow]:
        """获取活跃伏笔"""
        memory = self._get_or_create(story_id)
        return [f for f in memory.foreshadows if f.status == "active"]

    # ========== World State ==========

    def update_world_state(
        self,
        story_id: str,
        forces: dict[str, dict[str, str]] | None = None,
        locations: dict[str, dict[str, str]] | None = None,
        rules: dict[str, str] | None = None,
    ) -> None:
        """更新世界状态"""
        memory = self._get_or_create(story_id)
        ws = memory.world_state

        if forces:
            ws.forces.update(forces)
        if locations:
            ws.locations.update(locations)
        if rules:
            ws.rules.update(rules)

    def get_world_state(self, story_id: str) -> WorldState:
        """获取世界状态"""
        memory = self._get_or_create(story_id)
        return memory.world_state

    # ========== Context Assembly ==========

    def assemble_context(
        self,
        story_id: str,
        recent_chapters: int = 5,
    ) -> dict[str, Any]:
        """
        组装完整上下文（供 Agent 使用）

        Returns:
            包含 timeline, characters, foreshadows, world_state 的字典
        """
        memory = self._get_or_create(story_id)

        return {
            "timeline": [e.model_dump() for e in memory.timeline[-recent_chapters * 3:]],
            "characters": {
                name: char.model_dump()
                for name, char in memory.characters.items()
            },
            "foreshadows": [
                f.model_dump() for f in memory.foreshadows if f.status == "active"
            ],
            "world_state": memory.world_state.model_dump(),
        }

    def get_memory(self, story_id: str) -> NovelMemory:
        """获取完整记忆对象"""
        return self._get_or_create(story_id)


# 全局实例
memory_manager = MemoryManager()
