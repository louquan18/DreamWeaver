"""Initial schema - AI 域表 (StoryMemory / Checkpoint)

业务主数据表（stories / chapters / chapter_generations）由 Java 服务的 Flyway
迁移管理，本服务不再创建它们。本迁移只负责本服务拥有的 AI 域表，且不与业务表
建立跨服务外键（story_id / chapter_id 为普通索引 UUID）。

Revision ID: 001_initial
Revises:
Create Date: 2026-06-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── story_memories ───────────────────────────────────────
    op.create_table(
        "story_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("memory_type", sa.String(50), nullable=False, index=True),
        sa.Column("content", postgresql.JSONB, nullable=False),
        sa.Column("chapter_range", postgresql.ARRAY(sa.Integer), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "idx_memories_story_type",
        "story_memories",
        ["story_id", "memory_type"],
    )
    op.create_index(
        "idx_memories_content",
        "story_memories",
        ["content"],
        postgresql_using="gin",
    )

    # ── checkpoints ──────────────────────────────────────────
    op.create_table(
        "checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("execution_id", sa.String(100), nullable=False, unique=True),
        sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("chapter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("current_node", sa.String(100), nullable=True),
        sa.Column("state_snapshot", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "idx_checkpoints_execution",
        "checkpoints",
        ["execution_id"],
    )


def downgrade() -> None:
    op.drop_table("checkpoints")
    op.drop_table("story_memories")
