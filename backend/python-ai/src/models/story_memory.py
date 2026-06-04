"""小说记忆数据模型 (Timeline / Character / Foreshadow / World)"""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .story import Story


class StoryMemory(BaseModel):
    """结构化记忆存储

    memory_type 可选值:
      - timeline    时间线事件
      - character   人物状态与关系
      - foreshadow  伏笔记录
      - world       世界观设定
    """

    __tablename__ = "story_memories"

    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stories.id", ondelete="CASCADE"),
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

    # Relationships
    story: Mapped["Story"] = relationship(back_populates="memories")

    def __repr__(self) -> str:
        return f"<StoryMemory id={self.id} type={self.memory_type}>"
