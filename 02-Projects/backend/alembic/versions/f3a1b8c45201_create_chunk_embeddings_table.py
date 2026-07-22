"""create chunk_embeddings table

Revision ID: f3a1b8c45201
Revises: e8c5b6a30293
Create Date: 2026-07-22

Creates chunk_embeddings for embedding metadata linked to document chunks.
Vectors are stored in FAISS (Version 1). Deleting a chunk cascades to its
embedding metadata via ON DELETE CASCADE.

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f3a1b8c45201"
down_revision: Union[str, Sequence[str], None] = "e8c5b6a30293"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chunk_embeddings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chunk_id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["document_chunks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_id", name="uq_chunk_embeddings_chunk_id"),
    )
    op.create_index(
        op.f("ix_chunk_embeddings_id"),
        "chunk_embeddings",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_chunk_embeddings_chunk_id"),
        "chunk_embeddings",
        ["chunk_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_chunk_embeddings_chunk_id"), table_name="chunk_embeddings")
    op.drop_index(op.f("ix_chunk_embeddings_id"), table_name="chunk_embeddings")
    op.drop_table("chunk_embeddings")
