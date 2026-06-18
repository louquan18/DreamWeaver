"""小说记忆数据模型 (Timeline / Character / Foreshadow / World)"""

import uuid
from typing import Any

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class StoryMemory(BaseModel):
    """结构化记忆存储

    memory_type 可选值:
      - timeline    时间线事件
      - character   人物状态与关系
      - foreshadow  伏笔记录
      - world       世界观设定

    注: story_id 为普通索引 UUID，不设外键。业务表 stories 由 Java 服务拥有，
    本服务不与其建立跨服务外键约束，story_id 的合法性由调用方（Java）保证。
    """

    __tablename__ = "story_memories"

    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    memory_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    content: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    chapter_range: Mapped[list[int] | None] = mapped_column(
        ARRAY(Integer),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<StoryMemory id={self.id} type={self.memory_type}>"
