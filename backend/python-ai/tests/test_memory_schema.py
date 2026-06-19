"""Memory Schema 测试"""

import pytest
from pydantic import ValidationError

from src.memory.schema import (
    CharacterState,
    CompressionResult,
    CultivationState,
    Foreshadow,
    NovelMemory,
    Relationship,
    TimelineEvent,
    WorldState,
)


def test_timeline_event():
    e = TimelineEvent(chapter=1, event="test", characters=["c1"], importance="high")
    assert e.chapter == 1
    assert e.importance == "high"


def test_character_state():
    c = CharacterState(name="张三")
    assert c.name == "张三"
    assert isinstance(c.current_state, CultivationState)
    assert c.current_state.cultivation_level == ""
    assert c.current_state.health_status == "正常"
    assert c.relationships == {}


def test_relationship():
    r = Relationship(type="好友", closeness=80)
    assert r.type == "好友"


def test_foreshadow():
    f = Foreshadow(id="fs-1", chapter_planted=10, content="test")
    assert f.status == "planted"  # default
    assert f.attention_status == "normal"
    assert f.needs_attention is False


def test_foreshadow_lifecycle_statuses():
    for status in [
        "planned",
        "planted",
        "reinforced",
        "triggered",
        "revealed",
        "resolved",
        "abandoned",
    ]:
        f = Foreshadow(id=f"fs-{status}", chapter_planted=1, content="test", status=status)
        assert f.status == status


def test_foreshadow_rejects_invalid_lifecycle_status():
    with pytest.raises(ValidationError):
        Foreshadow(id="fs-invalid", chapter_planted=1, content="test", status="overdue_lifecycle")


def test_foreshadow_legacy_active_maps_to_planted():
    f = Foreshadow(id="fs-active", chapter_planted=1, content="test", status="active")
    assert f.status == "planted"
    assert f.attention_status == "normal"
    assert f.needs_attention is False


def test_foreshadow_legacy_overdue_maps_to_attention_status():
    f = Foreshadow(id="fs-overdue", chapter_planted=1, content="test", status="overdue")
    assert f.status == "planted"
    assert f.attention_status == "overdue"
    assert f.needs_attention is True


def test_world_state():
    ws = WorldState()
    assert ws.forces == {}
    assert ws.rules == {}


def test_novel_memory():
    m = NovelMemory()
    assert m.timeline == []
    assert m.characters == {}


def test_compression_result_rate():
    r = CompressionResult(
        summary="short",
        original_length=100,
        compressed_length=60,
    )
    rate = r.calculate_rate()
    assert rate == pytest.approx(0.4)
