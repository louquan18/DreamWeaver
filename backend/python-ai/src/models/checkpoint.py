"""Checkpoint 数据模型（LangGraph 断点恢复）"""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .story import Story


class Checkpoint(BaseModel):
    """LangGraph 工作流断点快照

    每个 Agent 节点执行完成后自动保存状态，
    服务重启或异常中断后可从中断点恢复。
    """

    __tablename__ = "checkpoints"

    execution_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )
    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chapters.id", ondelete="SET NULL"),
        nullable=True,
    )
    current_node: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    state_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    # Relationships
    story: Mapped["Story"] = relationship(back_populates="checkpoints")

    def __repr__(self) -> str:
        return f"<Checkpoint id={self.id} execution={self.execution_id} node={self.current_node}>"
