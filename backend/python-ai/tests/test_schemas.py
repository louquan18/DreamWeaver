"""Pydantic Schema 测试"""

import uuid

import pytest
from pydantic import ValidationError

from src.schemas import ChapterCreate, ChapterResponse, StoryCreate, StoryResponse, StoryUpdate


class TestStoryCreate:
    def test_valid(self):
        story = StoryCreate(title="Test Novel")
        assert story.title == "Test Novel"
        assert story.genre is None

    def test_with_all_fields(self):
        story = StoryCreate(
            title="Test",
            description="A test novel",
            genre="xuanhuan",
            target_words=100000,
        )
        assert story.target_words == 100000

    def test_empty_title_fails(self):
        with pytest.raises(ValidationError):
            StoryCreate(title="")

    def test_title_too_long(self):
        with pytest.raises(ValidationError):
            StoryCreate(title="x" * 201)


class TestStoryUpdate:
    def test_partial_update(self):
        update = StoryUpdate(title="New Title")
        assert update.title == "New Title"
        assert update.description is None

    def test_empty_update(self):
        update = StoryUpdate()
        assert update.model_dump(exclude_unset=True) == {}


class TestStoryResponse:
    def test_from_attributes(self):
        data = {
            "id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "title": "Test",
            "status": "draft",
            "created_at": "2026-06-04T00:00:00Z",
            "updated_at": "2026-06-04T00:00:00Z",
        }
        resp = StoryResponse(**data)
        assert resp.title == "Test"


class TestChapterCreate:
    def test_valid(self):
        ch = ChapterCreate(chapter_number=1, title="Prologue")
        assert ch.chapter_number == 1

    def test_number_must_be_positive(self):
        with pytest.raises(ValidationError):
            ChapterCreate(chapter_number=0)


class TestChapterResponse:
    def test_from_attributes(self):
        data = {
            "id": uuid.uuid4(),
            "story_id": uuid.uuid4(),
            "chapter_number": 1,
            "status": "draft",
            "created_at": "2026-06-04T00:00:00Z",
            "updated_at": "2026-06-04T00:00:00Z",
        }
        resp = ChapterResponse(**data)
        assert resp.chapter_number == 1
        assert resp.title is None
