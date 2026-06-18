"""Memory Manager - 统一记忆管理接口

支持双模式：
  - 有 DB 会话时：读写 PostgreSQL（持久化）
  - 无 DB 会话时：纯内存存储（开发/测试）
"""

import uuid
from typing import Any

from loguru import logger

from .schema import (
    CharacterState,
    CultivationState,
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

    双模式运行：
      - 调用 set_repository(db) 后走 PostgreSQL 持久化
      - 否则走内存存储（开发/测试用）
    """

    def __init__(self):
        self._store: dict[str, NovelMemory] = {}
        self._repo = None  # MemoryRepository | None

    def set_repository(self, repo) -> None:
        """注入数据库 Repository（启用持久化模式）"""
        self._repo = repo
        logger.info("[Memory] Repository injected, persistence enabled")

    def _get_or_create(self, story_id: str) -> NovelMemory:
        if story_id not in self._store:
            self._store[story_id] = NovelMemory()
        return self._store[story_id]

    # ========== Timeline ==========

    async def add_event(self, story_id: str, event: TimelineEvent) -> None:
        """添加时间线事件"""
        memory = self._get_or_create(story_id)
        memory.timeline.append(event)
        logger.debug(f"[Memory] Added event: {event.event[:50]}")

        # 持久化
        if self._repo:
            await self._save_memory(story_id, "timeline", {
                "events": [e.model_dump() for e in memory.timeline],
            })

    async def get_events(
        self,
        story_id: str,
        last_n: int | None = None,
        importance: str | None = None,
    ) -> list[TimelineEvent]:
        """获取时间线事件"""
        # 优先从 DB 加载
        if self._repo:
            await self._load_from_db(story_id, "timeline")

        memory = self._get_or_create(story_id)
        events = memory.timeline

        if importance:
            events = [e for e in events if e.importance == importance]
        if last_n:
            events = events[-last_n:]
        return events

    # ========== Character Graph ==========

    async def update_character(
        self,
        story_id: str,
        name: str,
        state_update: dict[str, Any] | None = None,
        chapter: int = 0,
    ) -> None:
        """更新人物状态（字段级合并，空值不覆盖，list 追加不重复）"""
        memory = self._get_or_create(story_id)

        if name not in memory.characters:
            memory.characters[name] = CharacterState(name=name)

        char = memory.characters[name]
        if state_update:
            for field_name in CultivationState.model_fields:
                new_val = state_update.get(field_name)
                if new_val is not None and new_val != "":
                    setattr(char.current_state, field_name, new_val)
            # list 类型字段：追加而非覆盖
            for list_field in ("special_abilities", "equipment"):
                additions = state_update.get(f"{list_field}_added")
                if additions:
                    existing = getattr(char.current_state, list_field)
                    for item in additions:
                        if item not in existing:
                            existing.append(item)
        if chapter > 0:
            char.last_appeared = chapter

        if self._repo:
            await self._save_memory(story_id, "character", {
                n: c.model_dump() for n, c in memory.characters.items()
            })

    async def add_relationship(
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
            type=rel_type, closeness=closeness,
        )

        if self._repo:
            await self._save_memory(story_id, "character", {
                name: c.model_dump() for name, c in memory.characters.items()
            })

    async def get_characters(self, story_id: str) -> dict[str, CharacterState]:
        """获取所有人物"""
        if self._repo:
            await self._load_from_db(story_id, "character")
        return self._get_or_create(story_id).characters

    async def get_character(self, story_id: str, name: str) -> CharacterState | None:
        """获取单个人物"""
        if self._repo:
            await self._load_from_db(story_id, "character")
        return self._get_or_create(story_id).characters.get(name)

    # ========== Foreshadow ==========

    async def add_foreshadow(self, story_id: str, foreshadow: Foreshadow) -> None:
        """添加伏笔"""
        memory = self._get_or_create(story_id)
        memory.foreshadows.append(foreshadow)

        if self._repo:
            await self._save_memory(story_id, "foreshadow", {
                "foreshadows": [f.model_dump() for f in memory.foreshadows],
            })

    async def resolve_foreshadow(self, story_id: str, foreshadow_id: str) -> bool:
        """回收伏笔"""
        memory = self._get_or_create(story_id)
        for fs in memory.foreshadows:
            if fs.id == foreshadow_id and fs.status == "active":
                fs.status = "resolved"
                if self._repo:
                    await self._save_memory(story_id, "foreshadow", {
                        "foreshadows": [f.model_dump() for f in memory.foreshadows],
                    })
                return True
        return False

    async def get_active_foreshadows(self, story_id: str) -> list[Foreshadow]:
        """获取活跃伏笔"""
        if self._repo:
            await self._load_from_db(story_id, "foreshadow")
        memory = self._get_or_create(story_id)
        return [f for f in memory.foreshadows if f.status == "active"]

    async def age_foreshadows(self, story_id: str, current_chapter: int) -> list[Foreshadow]:
        """
        每章创作前调用：更新伏笔年龄，超期标记为 overdue。

        Returns:
            需要告警的伏笔列表（overdue 的）
        """
        memory = self._get_or_create(story_id)
        alerts = []
        for fs in memory.foreshadows:
            if fs.status == "active":
                fs.age = current_chapter - fs.chapter_planted
                if fs.age > fs.max_age:
                    fs.status = "overdue"
                    alerts.append(fs)
                    logger.warning(
                        f"[Memory] Foreshadow {fs.id} overdue: planted ch{fs.chapter_planted}, "
                        f"age={fs.age} > max_age={fs.max_age}"
                    )
        if alerts and self._repo:
            await self._save_memory(story_id, "foreshadow", {
                "foreshadows": [f.model_dump() for f in memory.foreshadows],
            })
        return alerts

    # ========== World State ==========

    async def update_world_state(
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

        if self._repo:
            await self._save_memory(story_id, "world", ws.model_dump())

    async def get_world_state(self, story_id: str) -> WorldState:
        """获取世界状态"""
        if self._repo:
            await self._load_from_db(story_id, "world")
        return self._get_or_create(story_id).world_state

    # ========== Context Assembly ==========

    async def assemble_context(
        self,
        story_id: str,
        recent_chapters: int = 5,
    ) -> dict[str, Any]:
        """
        组装完整上下文（供 Agent 使用）

        Returns:
            {timeline, characters, foreshadows, world_state}
        """
        # 从 DB 加载所有记忆类型
        if self._repo:
            for mtype in ["timeline", "character", "foreshadow", "world"]:
                await self._load_from_db(story_id, mtype)

        memory = self._get_or_create(story_id)

        # 时间线：加权选取，保留 permanent + 高重要度 + 最近事件
        timeline = self._select_timeline_events(memory.timeline, max_count=20)

        # 伏笔：overdue 排最前，然后按 importance 排序，限制 10 个
        active_foreshadows = [
            f for f in memory.foreshadows if f.status in ("active", "overdue")
        ]
        importance_order = {"high": 0, "medium": 1, "low": 2}
        active_foreshadows.sort(
            key=lambda f: (0 if f.status == "overdue" else 1, importance_order.get(f.importance, 1))
        )

        return {
            "timeline": [e.model_dump() for e in timeline],
            "characters": {
                name: char.model_dump()
                for name, char in memory.characters.items()
            },
            "foreshadows": [f.model_dump() for f in active_foreshadows[:10]],
            "world_state": memory.world_state.model_dump(),
        }

    @staticmethod
    def _select_timeline_events(
        events: list[TimelineEvent],
        max_count: int = 20,
    ) -> list[TimelineEvent]:
        """加权选取时间线事件：permanent 常驻 + 高重要度优先 + 最近事件补充"""
        if len(events) <= max_count:
            return events

        permanent = [e for e in events if e.is_permanent]
        non_permanent = [e for e in events if not e.is_permanent]
        high_importance = [e for e in non_permanent if e.importance == "high"]

        remaining_slots = max_count - len(permanent) - len(high_importance)
        recent = non_permanent[-max(remaining_slots, 3):] if remaining_slots > 0 else []

        selected = permanent + high_importance + recent
        # 去重
        seen: set[tuple[int, str]] = set()
        deduped = []
        for e in selected:
            key = (e.chapter, e.event)
            if key not in seen:
                seen.add(key)
                deduped.append(e)

        return sorted(deduped, key=lambda e: e.chapter)[-max_count:]

    def get_memory(self, story_id: str) -> NovelMemory:
        """获取完整记忆对象"""
        return self._get_or_create(story_id)

    # ========== Private: DB Persistence ==========

    async def _save_memory(self, story_id: str, memory_type: str, content: dict) -> None:
        """保存到 PostgreSQL"""
        try:
            story_uuid = uuid.UUID(story_id)
        except ValueError:
            story_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, story_id)

        try:
            # 查找已有记录，有则更新，无则创建
            # 注: story 主数据由 Java 服务创建（生成任务触发前已存在）；
            # 本服务只写自己的 story_memories，story_id 不再设外键，无需在此自动建 story。
            existing = await self._repo.get_latest_memory(story_uuid, memory_type)
            if existing:
                await self._repo.update_memory(existing.id, content)
            else:
                await self._repo.save_memory(story_uuid, memory_type, content)
        except Exception as e:
            logger.warning(f"[Memory] DB save failed for {memory_type}: {e}")

    async def _load_from_db(self, story_id: str, memory_type: str) -> None:
        """从 PostgreSQL 加载到内存"""
        try:
            story_uuid = uuid.UUID(story_id)
        except ValueError:
            story_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, story_id)

        try:
            record = await self._repo.get_latest_memory(story_uuid, memory_type)
            if not record:
                return

            content = record.content
            memory = self._get_or_create(story_id)

            if memory_type == "timeline" and "events" in content:
                memory.timeline = [TimelineEvent(**e) for e in content["events"]]
            elif memory_type == "character":
                memory.characters = {
                    name: CharacterState(**data)
                    for name, data in content.items()
                }
            elif memory_type == "foreshadow" and "foreshadows" in content:
                memory.foreshadows = [Foreshadow(**f) for f in content["foreshadows"]]
            elif memory_type == "world":
                memory.world_state = WorldState(**content)

        except Exception as e:
            logger.warning(f"[Memory] DB load failed for {memory_type}: {e}")


# 全局实例
memory_manager = MemoryManager()
