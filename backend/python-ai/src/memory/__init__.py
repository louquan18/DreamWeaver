"""结构化记忆系统"""

from .compression import compress_chapter, extract_events, extract_character_changes, generate_summary
from .manager import MemoryManager, memory_manager
from .schema import (
    CharacterState,
    CompressionResult,
    CultivationState,
    Foreshadow,
    NovelMemory,
    Relationship,
    TimelineEvent,
    WorldState,
)
from .vector_store import (
    add_chapter_fulltext,
    add_chapter_summary,
    get_collection_stats,
    get_fulltext_stats,
    search_relevant_chapters,
    search_relevant_paragraphs,
)

__all__ = [
    "compress_chapter",
    "extract_events",
    "extract_character_changes",
    "generate_summary",
    "MemoryManager",
    "memory_manager",
    "CharacterState",
    "CompressionResult",
    "CultivationState",
    "Foreshadow",
    "NovelMemory",
    "Relationship",
    "TimelineEvent",
    "WorldState",
    "add_chapter_fulltext",
    "add_chapter_summary",
    "get_collection_stats",
    "get_fulltext_stats",
    "search_relevant_chapters",
    "search_relevant_paragraphs",
]
