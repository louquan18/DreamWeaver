"""Add content column to chapters

Revision ID: 002_add_content
Revises: 001_initial
Create Date: 2026-06-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_add_content"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chapters", sa.Column("content", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("chapters", "content")
