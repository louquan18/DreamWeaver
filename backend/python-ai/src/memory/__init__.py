"""结构化记忆系统"""

from .compression import compress_chapter, extract_events, extract_character_changes, generate_summary
from .manager import MemoryManager, memory_manager
from .schema import (
    CharacterState,
    CompressionResult,
    Foreshadow,
    NovelMemory,
    Relationship,
    TimelineEvent,
    WorldState,
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
    "Foreshadow",
    "NovelMemory",
    "Relationship",
    "TimelineEvent",
    "WorldState",
]
