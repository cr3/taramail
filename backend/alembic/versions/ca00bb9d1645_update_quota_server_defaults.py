"""Update quota server defaults

Revision ID: ca00bb9d1645
Revises: f3adbeb27923
Create Date: 2025-10-31 18:27:27.455694

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ca00bb9d1645'
down_revision: str | None = 'f3adbeb27923'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("domain", "defquota", server_default=sa.text("3221225472"))
    op.alter_column("domain", "maxquota", server_default=sa.text("107374182400"))
    op.alter_column("domain", "quota", server_default=sa.text("107374182400"))
    op.alter_column("mailbox", "quota", server_default=None)


def downgrade() -> None:
    op.alter_column("mailbox", "quota", server_default=sa.text("3072"))
    op.alter_column("domain", "quota", server_default=sa.text("102400"))
    op.alter_column("domain", "maxquota", server_default=sa.text("102400"))
    op.alter_column("domain", "defquota", server_default=sa.text("3072"))
