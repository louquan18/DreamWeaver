"""Pydantic 数据验证模型"""

from .story import StoryCreate, StoryUpdate, StoryResponse
from .chapter import ChapterCreate, ChapterUpdate, ChapterResponse

__all__ = [
    "StoryCreate",
    "StoryUpdate",
    "StoryResponse",
    "ChapterCreate",
    "ChapterUpdate",
    "ChapterResponse",
]
