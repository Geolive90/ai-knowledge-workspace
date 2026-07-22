"""add user_id to documents

Revision ID: c4a8f2e19061
Revises: bdc259e18150
Create Date: 2026-07-18

Legacy document rows without an owner are assigned to documenttest@example.com
because that is the documented account used for existing document upload tests
(see BUILD_LOG.md). The migration never deletes document rows. If that user
does not exist when legacy rows are present, or if any row remains without an
owner after backfill, the migration aborts with RuntimeError.

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c4a8f2e19061"
down_revision: Union[str, Sequence[str], None] = "bdc259e18150"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEGACY_DOCUMENT_OWNER_EMAIL = "documenttest@example.com"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "documents" not in tables:
        op.create_table(
            "documents",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("filename", sa.String(), nullable=False),
            sa.Column("file_path", sa.String(), nullable=False),
            sa.Column("uploaded_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_documents_id"), "documents", ["id"], unique=False)
        op.create_index(
            op.f("ix_documents_user_id"), "documents", ["user_id"], unique=False
        )
        return

    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))

    document_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM documents")
    ).scalar_one()

    if document_count > 0:
        owner = bind.execute(
            sa.text("SELECT id FROM users WHERE email = :email"),
            {"email": LEGACY_DOCUMENT_OWNER_EMAIL},
        ).first()

        if owner is None:
            raise RuntimeError(
                "Migration aborted: documents exist but "
                f"{LEGACY_DOCUMENT_OWNER_EMAIL!r} was not found. "
                "Create that user or assign owners manually before retrying."
            )

        owner_id = owner[0]

        bind.execute(
            sa.text(
                "UPDATE documents SET user_id = :owner_id WHERE user_id IS NULL"
            ),
            {"owner_id": owner_id},
        )

        remaining_null = bind.execute(
            sa.text("SELECT COUNT(*) FROM documents WHERE user_id IS NULL")
        ).scalar_one()

        if remaining_null > 0:
            raise RuntimeError(
                f"Migration aborted: {remaining_null} document row(s) still have "
                "NULL user_id after backfill. No rows were deleted."
            )

    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.alter_column("user_id", nullable=False)
        batch_op.create_foreign_key(
            "fk_documents_user_id_users",
            "users",
            ["user_id"],
            ["id"],
        )
        batch_op.create_index("ix_documents_user_id", ["user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("documents")}

    if "user_id" not in columns:
        return

    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.drop_index("ix_documents_user_id")
        batch_op.drop_constraint("fk_documents_user_id_users", type_="foreignkey")
        batch_op.drop_column("user_id")
