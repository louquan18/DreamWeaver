"""记忆系统单元测试"""

import pytest

from src.memory import (
    CharacterState,
    CultivationState,
    Foreshadow,
    MemoryManager,
    Relationship,
    TimelineEvent,
    WorldState,
)


@pytest.fixture
def manager():
    return MemoryManager()


# ========== Timeline Tests ==========


class TestTimeline:
    @pytest.mark.asyncio
    async def test_add_and_get_event(self, manager):
        event = TimelineEvent(
            chapter=1,
            event="主角获得系统",
            characters=["主角"],
            importance="high",
        )
        await manager.add_event("s1", event)

        events = await manager.get_events("s1")
        assert len(events) == 1
        assert events[0].event == "主角获得系统"

    @pytest.mark.asyncio
    async def test_get_events_last_n(self, manager):
        for i in range(10):
            await manager.add_event("s1", TimelineEvent(chapter=i, event=f"event-{i}"))

        events = await manager.get_events("s1", last_n=3)
        assert len(events) == 3
        assert events[0].event == "event-7"

    @pytest.mark.asyncio
    async def test_get_events_filter_importance(self, manager):
        await manager.add_event("s1", TimelineEvent(chapter=1, event="e1", importance="high"))
        await manager.add_event("s1", TimelineEvent(chapter=2, event="e2", importance="low"))
        await manager.add_event("s1", TimelineEvent(chapter=3, event="e3", importance="high"))

        events = await manager.get_events("s1", importance="high")
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_empty_events(self, manager):
        events = await manager.get_events("nonexistent")
        assert events == []


# ========== Character Graph Tests ==========


class TestCharacterGraph:
    @pytest.mark.asyncio
    async def test_update_character(self, manager):
        await manager.update_character("s1", "张三", {"cultivation_level": "炼气三层"}, chapter=10)

        char = await manager.get_character("s1", "张三")
        assert char is not None
        assert char.name == "张三"
        assert char.current_state.cultivation_level == "炼气三层"
        assert char.last_appeared == 10

    @pytest.mark.asyncio
    async def test_update_character_incremental(self, manager):
        await manager.update_character("s1", "张三", {"cultivation_level": "炼气三层"})
        await manager.update_character("s1", "张三", {"location": "天元城"})

        char = await manager.get_character("s1", "张三")
        assert char.current_state.cultivation_level == "炼气三层"
        assert char.current_state.location == "天元城"

    @pytest.mark.asyncio
    async def test_update_character_list_append(self, manager):
        await manager.update_character("s1", "张三", {"special_abilities_added": ["火球术"]})
        await manager.update_character("s1", "张三", {"special_abilities_added": ["冰锥术"]})

        char = await manager.get_character("s1", "张三")
        assert "火球术" in char.current_state.special_abilities
        assert "冰锥术" in char.current_state.special_abilities

    @pytest.mark.asyncio
    async def test_update_character_empty_no_overwrite(self, manager):
        await manager.update_character("s1", "张三", {"cultivation_level": "筑基", "location": "天剑山"})
        await manager.update_character("s1", "张三", {"location": "青云镇"})

        char = await manager.get_character("s1", "张三")
        assert char.current_state.cultivation_level == "筑基"
        assert char.current_state.location == "青云镇"

    @pytest.mark.asyncio
    async def test_add_relationship(self, manager):
        await manager.add_relationship("s1", "张三", "李四", "好友", closeness=80)

        char = await manager.get_character("s1", "张三")
        assert "李四" in char.relationships
        assert char.relationships["李四"].type == "好友"

    @pytest.mark.asyncio
    async def test_get_characters(self, manager):
        await manager.update_character("s1", "张三")
        await manager.update_character("s1", "李四")

        chars = await manager.get_characters("s1")
        assert len(chars) == 2

    @pytest.mark.asyncio
    async def test_get_nonexistent_character(self, manager):
        char = await manager.get_character("s1", "不存在")
        assert char is None


# ========== Foreshadow Tests ==========


class TestForeshadow:
    @pytest.mark.asyncio
    async def test_add_and_get_foreshadow(self, manager):
        fs = Foreshadow(
            id="fs-001",
            chapter_planted=10,
            content="神秘老人提到上古秘境",
            trigger_condition="主角达到100级",
            status="active",
            importance="high",
        )
        await manager.add_foreshadow("s1", fs)

        active = await manager.get_active_foreshadows("s1")
        assert len(active) == 1
        assert active[0].id == "fs-001"

    @pytest.mark.asyncio
    async def test_resolve_foreshadow(self, manager):
        fs = Foreshadow(id="fs-001", chapter_planted=10, content="test")
        await manager.add_foreshadow("s1", fs)

        result = await manager.resolve_foreshadow("s1", "fs-001")
        assert result is True

        active = await manager.get_active_foreshadows("s1")
        assert len(active) == 0

    @pytest.mark.asyncio
    async def test_resolve_nonexistent(self, manager):
        result = await manager.resolve_foreshadow("s1", "nonexistent")
        assert result is False


# ========== World State Tests ==========


class TestWorldStateManager:
    @pytest.mark.asyncio
    async def test_update_world_state(self, manager):
        await manager.update_world_state(
            "s1",
            forces={"天元宗": {"strength": "strong", "attitude": "friendly"}},
            rules={"修炼体系": "炼气→筑基→金丹"},
        )

        ws = await manager.get_world_state("s1")
        assert ws.forces["天元宗"]["strength"] == "strong"
        assert ws.rules["修炼体系"] == "炼气→筑基→金丹"

    @pytest.mark.asyncio
    async def test_incremental_update(self, manager):
        await manager.update_world_state("s1", rules={"修炼体系": "炼气→筑基"})
        await manager.update_world_state("s1", rules={"等级上限": "200"})

        ws = await manager.get_world_state("s1")
        assert len(ws.rules) == 2


# ========== Context Assembly Tests ==========


class TestContextAssembly:
    @pytest.mark.asyncio
    async def test_assemble_context(self, manager):
        await manager.add_event("s1", TimelineEvent(chapter=1, event="e1"))
        await manager.update_character("s1", "张三", {"level": 10})
        await manager.add_foreshadow("s1", Foreshadow(id="fs-1", chapter_planted=1, content="test"))
        await manager.update_world_state("s1", rules={"r1": "v1"})

        ctx = await manager.assemble_context("s1")
        assert len(ctx["timeline"]) == 1
        assert "张三" in ctx["characters"]
        assert len(ctx["foreshadows"]) == 1
        assert ctx["world_state"]["rules"]["r1"] == "v1"

    @pytest.mark.asyncio
    async def test_assemble_empty_context(self, manager):
        ctx = await manager.assemble_context("new_story")
        assert ctx["timeline"] == []
        assert ctx["characters"] == {}
        assert ctx["foreshadows"] == []

    @pytest.mark.asyncio
    async def test_timeline_permanent_events_kept(self, manager):
        """permanent 事件在超出数量限制时仍被保留"""
        # 添加 25 个非 permanent 事件 + 1 个 permanent 事件
        for i in range(25):
            await manager.add_event("s1", TimelineEvent(chapter=i, event=f"event-{i}"))
        await manager.add_event("s1", TimelineEvent(
            chapter=0, event="主角觉醒", importance="high", is_permanent=True,
        ))

        ctx = await manager.assemble_context("s1")
        events = ctx["timeline"]
        assert len(events) <= 20
        permanent_events = [e for e in events if e.get("is_permanent")]
        assert len(permanent_events) == 1
        assert permanent_events[0]["event"] == "主角觉醒"

    @pytest.mark.asyncio
    async def test_foreshadow_overdue_sorting(self, manager):
        """overdue 伏笔排在 active 之前"""
        await manager.add_foreshadow("s1", Foreshadow(
            id="fs-active", chapter_planted=10, content="普通伏笔", importance="high",
        ))
        fs_overdue = Foreshadow(id="fs-overdue", chapter_planted=1, content="过期伏笔", importance="medium")
        fs_overdue.status = "overdue"
        await manager.add_foreshadow("s1", fs_overdue)

        ctx = await manager.assemble_context("s1")
        foreshadows = ctx["foreshadows"]
        assert foreshadows[0]["id"] == "fs-overdue"
        assert foreshadows[1]["id"] == "fs-active"


# ========== Foreshadow Aging Tests ==========


class TestForeshadowAging:
    @pytest.mark.asyncio
    async def test_age_foreshadows_marks_overdue(self, manager):
        """伏笔超过 max_age 后标记为 overdue"""
        await manager.add_foreshadow("s1", Foreshadow(
            id="fs-001", chapter_planted=1, content="test", max_age=5,
        ))

        alerts = await manager.age_foreshadows("s1", current_chapter=7)
        assert len(alerts) == 1
        assert alerts[0].status == "overdue"
        assert alerts[0].age == 6

    @pytest.mark.asyncio
    async def test_age_foreshadows_within_limit(self, manager):
        """伏笔未超期时保持 active"""
        await manager.add_foreshadow("s1", Foreshadow(
            id="fs-001", chapter_planted=5, content="test", max_age=20,
        ))

        alerts = await manager.age_foreshadows("s1", current_chapter=10)
        assert len(alerts) == 0

        active = await manager.get_active_foreshadows("s1")
        assert len(active) == 1
        assert active[0].age == 5


# ========== Timeline Selection Tests ==========


class TestTimelineSelection:
    def test_select_within_limit(self, manager):
        """事件数未超限时全部返回"""
        events = [TimelineEvent(chapter=i, event=f"e{i}") for i in range(5)]
        result = MemoryManager._select_timeline_events(events, max_count=20)
        assert len(result) == 5

    def test_select_permanent_always_kept(self, manager):
        """permanent 事件始终保留"""
        events = [TimelineEvent(chapter=i, event=f"e{i}") for i in range(25)]
        events.append(TimelineEvent(chapter=0, event="关键转折", is_permanent=True))
        result = MemoryManager._select_timeline_events(events, max_count=20)
        perm = [e for e in result if e.is_permanent]
        assert len(perm) == 1

    def test_select_high_importance_prioritized(self, manager):
        """高重要度事件优先于低重要度"""
        events = []
        for i in range(25):
            imp = "high" if i < 5 else "low"
            events.append(TimelineEvent(chapter=i, event=f"e{i}", importance=imp))
        result = MemoryManager._select_timeline_events(events, max_count=20)
        high_in_result = [e for e in result if e.importance == "high"]
        assert len(high_in_result) == 5  # 所有 high 都保留
