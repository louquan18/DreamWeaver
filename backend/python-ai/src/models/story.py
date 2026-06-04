"""小说数据模型"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .chapter import Chapter
    from .story_memory import StoryMemory
    from .checkpoint import Checkpoint


class Story(BaseModel):
    """小说"""

    __tablename__ = "stories"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    genre: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    target_words: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        server_default="draft",
    )

    # Relationships
    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="story",
        cascade="all, delete-orphan",
        order_by="Chapter.chapter_number",
    )
    memories: Mapped[list["StoryMemory"]] = relationship(
        back_populates="story",
        cascade="all, delete-orphan",
    )
    checkpoints: Mapped[list["Checkpoint"]] = relationship(
        back_populates="story",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Story id={self.id} title={self.title!r}>"
