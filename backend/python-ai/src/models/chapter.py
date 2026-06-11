"""章节数据模型"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .story import Story


class Chapter(BaseModel):
    """章节"""

    __tablename__ = "chapters"
    __table_args__ = (
        UniqueConstraint("story_id", "chapter_number", name="uq_chapter_story_number"),
    )

    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        server_default="draft",
    )

    # Relationships
    story: Mapped["Story"] = relationship(back_populates="chapters")

    def __repr__(self) -> str:
        return f"<Chapter id={self.id} number={self.chapter_number} title={self.title!r}>"
