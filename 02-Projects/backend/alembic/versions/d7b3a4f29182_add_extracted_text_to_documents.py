"""add extracted_text to documents

Revision ID: d7b3a4f29182
Revises: c4a8f2e19061
Create Date: 2026-07-20

Adds nullable extracted_text column for persistent document text storage.
Existing document rows are left unchanged. No backfill is performed.

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d7b3a4f29182"
down_revision: Union[str, Sequence[str], None] = "c4a8f2e19061"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.add_column(sa.Column("extracted_text", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.drop_column("extracted_text")
