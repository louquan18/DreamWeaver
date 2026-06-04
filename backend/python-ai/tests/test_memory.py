"""记忆系统单元测试"""

import pytest

from src.memory import (
    CharacterState,
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
    def test_add_and_get_event(self, manager):
        event = TimelineEvent(
            chapter=1,
            event="主角获得系统",
            characters=["主角"],
            importance="high",
        )
        manager.add_event("s1", event)

        events = manager.get_events("s1")
        assert len(events) == 1
        assert events[0].event == "主角获得系统"

    def test_get_events_last_n(self, manager):
        for i in range(10):
            manager.add_event("s1", TimelineEvent(chapter=i, event=f"event-{i}"))

        events = manager.get_events("s1", last_n=3)
        assert len(events) == 3
        assert events[0].event == "event-7"

    def test_get_events_filter_importance(self, manager):
        manager.add_event("s1", TimelineEvent(chapter=1, event="e1", importance="high"))
        manager.add_event("s1", TimelineEvent(chapter=2, event="e2", importance="low"))
        manager.add_event("s1", TimelineEvent(chapter=3, event="e3", importance="high"))

        events = manager.get_events("s1", importance="high")
        assert len(events) == 2

    def test_empty_events(self, manager):
        events = manager.get_events("nonexistent")
        assert events == []


# ========== Character Graph Tests ==========


class TestCharacterGraph:
    def test_update_character(self, manager):
        manager.update_character("s1", "张三", {"level": 50}, chapter=10)

        char = manager.get_character("s1", "张三")
        assert char is not None
        assert char.name == "张三"
        assert char.current_state["level"] == 50
        assert char.last_appeared == 10

    def test_update_character_incremental(self, manager):
        manager.update_character("s1", "张三", {"level": 10})
        manager.update_character("s1", "张三", {"location": "天元城"})

        char = manager.get_character("s1", "张三")
        assert char.current_state["level"] == 10
        assert char.current_state["location"] == "天元城"

    def test_add_relationship(self, manager):
        manager.add_relationship("s1", "张三", "李四", "好友", closeness=80)

        char = manager.get_character("s1", "张三")
        assert "李四" in char.relationships
        assert char.relationships["李四"].type == "好友"

    def test_get_characters(self, manager):
        manager.update_character("s1", "张三")
        manager.update_character("s1", "李四")

        chars = manager.get_characters("s1")
        assert len(chars) == 2

    def test_get_nonexistent_character(self, manager):
        char = manager.get_character("s1", "不存在")
        assert char is None


# ========== Foreshadow Tests ==========


class TestForeshadow:
    def test_add_and_get_foreshadow(self, manager):
        fs = Foreshadow(
            id="fs-001",
            chapter_planted=10,
            content="神秘老人提到上古秘境",
            trigger_condition="主角达到100级",
            status="active",
            importance="high",
        )
        manager.add_foreshadow("s1", fs)

        active = manager.get_active_foreshadows("s1")
        assert len(active) == 1
        assert active[0].id == "fs-001"

    def test_resolve_foreshadow(self, manager):
        fs = Foreshadow(id="fs-001", chapter_planted=10, content="test")
        manager.add_foreshadow("s1", fs)

        result = manager.resolve_foreshadow("s1", "fs-001")
        assert result is True

        active = manager.get_active_foreshadows("s1")
        assert len(active) == 0

    def test_resolve_nonexistent(self, manager):
        result = manager.resolve_foreshadow("s1", "nonexistent")
        assert result is False


# ========== World State Tests ==========


class TestWorldStateManager:
    def test_update_world_state(self, manager):
        manager.update_world_state(
            "s1",
            forces={"天元宗": {"strength": "strong", "attitude": "friendly"}},
            rules={"修炼体系": "炼气→筑基→金丹"},
        )

        ws = manager.get_world_state("s1")
        assert ws.forces["天元宗"]["strength"] == "strong"
        assert ws.rules["修炼体系"] == "炼气→筑基→金丹"

    def test_incremental_update(self, manager):
        manager.update_world_state("s1", rules={"修炼体系": "炼气→筑基"})
        manager.update_world_state("s1", rules={"等级上限": "200"})

        ws = manager.get_world_state("s1")
        assert len(ws.rules) == 2


# ========== Context Assembly Tests ==========


class TestContextAssembly:
    def test_assemble_context(self, manager):
        manager.add_event("s1", TimelineEvent(chapter=1, event="e1"))
        manager.update_character("s1", "张三", {"level": 10})
        manager.add_foreshadow("s1", Foreshadow(id="fs-1", chapter_planted=1, content="test"))
        manager.update_world_state("s1", rules={"r1": "v1"})

        ctx = manager.assemble_context("s1")
        assert len(ctx["timeline"]) == 1
        assert "张三" in ctx["characters"]
        assert len(ctx["foreshadows"]) == 1
        assert ctx["world_state"]["rules"]["r1"] == "v1"

    def test_assemble_empty_context(self, manager):
        ctx = manager.assemble_context("new_story")
        assert ctx["timeline"] == []
        assert ctx["characters"] == {}
        assert ctx["foreshadows"] == []
