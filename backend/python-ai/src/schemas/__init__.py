"""Pydantic schemas for API and AI service boundaries."""

from .blueprint import LightBlueprintGenerateRequest, NovelBlueprintDraft
from .outline import (
    CHAPTER_OUTLINE_CONTENT_JSON_SCHEMA,
    CHAPTER_OUTLINE_OPTION_JSON_SCHEMA,
    CHAPTER_OUTLINE_OPTIONS_JSON_SCHEMA,
    ChapterOutlineContent,
    ChapterOutlineDraft,
    ChapterOutlineOptionDraft,
    ChapterOutlineOptionsDraft,
    ConfirmedChapterOutlineDraft,
    chapter_outline_content_json_schema,
    chapter_outline_option_json_schema,
    chapter_outline_options_json_schema,
)

__all__ = [
    "CHAPTER_OUTLINE_CONTENT_JSON_SCHEMA",
    "CHAPTER_OUTLINE_OPTION_JSON_SCHEMA",
    "CHAPTER_OUTLINE_OPTIONS_JSON_SCHEMA",
    "ChapterOutlineContent",
    "ChapterOutlineDraft",
    "ChapterOutlineOptionDraft",
    "ChapterOutlineOptionsDraft",
    "ConfirmedChapterOutlineDraft",
    "LightBlueprintGenerateRequest",
    "NovelBlueprintDraft",
    "chapter_outline_content_json_schema",
    "chapter_outline_option_json_schema",
    "chapter_outline_options_json_schema",
]
