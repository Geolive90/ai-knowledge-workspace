"""add document indexing fields

Revision ID: a7c2d9e48103
Revises: f3a1b8c45201
Create Date: 2026-07-22

Adds indexing lifecycle columns to documents for Phase 4D orchestration.

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a7c2d9e48103"
down_revision: Union[str, Sequence[str], None] = "f3a1b8c45201"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "indexing_status",
                sa.String(length=32),
                nullable=False,
                server_default="pending",
            )
        )
        batch_op.add_column(sa.Column("indexing_error", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("indexed_at", sa.DateTime(), nullable=True))
        batch_op.add_column(
            sa.Column("indexing_started_at", sa.DateTime(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.drop_column("indexing_started_at")
        batch_op.drop_column("indexed_at")
        batch_op.drop_column("indexing_error")
        batch_op.drop_column("indexing_status")
