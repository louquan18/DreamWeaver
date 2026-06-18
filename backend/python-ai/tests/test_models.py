"""SQLAlchemy 模型单元测试"""

import uuid

from src.models import Checkpoint, StoryMemory


def test_story_memory_table_name():
    assert StoryMemory.__tablename__ == "story_memories"


def test_checkpoint_table_name():
    assert Checkpoint.__tablename__ == "checkpoints"


def test_story_memory_instance():
    memory = StoryMemory(
        story_id=uuid.uuid4(),
        memory_type="timeline",
        content={"events": [{"chapter": 1, "event": "test"}]},
    )
    assert memory.memory_type == "timeline"
    assert "events" in memory.content


def test_checkpoint_instance():
    cp = Checkpoint(
        execution_id="exec-001",
        story_id=uuid.uuid4(),
        current_node="generate_draft",
        state_snapshot={"key": "value"},
    )
    assert cp.execution_id == "exec-001"
    assert cp.current_node == "generate_draft"
