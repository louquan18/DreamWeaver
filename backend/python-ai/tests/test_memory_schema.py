"""Memory Schema 测试"""

from src.memory.schema import (
    CharacterState,
    CompressionResult,
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
    assert c.current_state == {}
    assert c.relationships == {}


def test_relationship():
    r = Relationship(type="好友", closeness=80)
    assert r.type == "好友"


def test_foreshadow():
    f = Foreshadow(id="fs-1", chapter_planted=10, content="test")
    assert f.status == "active"  # default


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


import pytest
