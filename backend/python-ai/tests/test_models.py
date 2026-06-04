"""SQLAlchemy 模型单元测试"""

import uuid

from src.models import Chapter, Checkpoint, Story, StoryMemory


def test_story_table_name():
    assert Story.__tablename__ == "stories"


def test_chapter_table_name():
    assert Chapter.__tablename__ == "chapters"


def test_story_memory_table_name():
    assert StoryMemory.__tablename__ == "story_memories"


def test_checkpoint_table_name():
    assert Checkpoint.__tablename__ == "checkpoints"


def test_story_instance():
    story = Story(
        user_id=uuid.uuid4(),
        title="Test Novel",
        genre="xuanhuan",
    )
    assert story.title == "Test Novel"
    assert story.genre == "xuanhuan"
    # server_default applies at DB level; in-memory instance has None until flushed
    assert story.status is None or story.status == "draft"


def test_chapter_instance():
    story_id = uuid.uuid4()
    chapter = Chapter(
        story_id=story_id,
        chapter_number=1,
        title="Chapter 1",
    )
    assert chapter.story_id == story_id
    assert chapter.chapter_number == 1


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
