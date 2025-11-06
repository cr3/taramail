"""Add internal column to alias.

Revision ID: 79d64ba432c7
Revises: ca00bb9d1645
Create Date: 2025-11-04 17:17:34.304607

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '79d64ba432c7'
down_revision: str | None = 'ca00bb9d1645'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("alias", "active", server_default=sa.text("1"))
    op.add_column('alias', sa.Column('internal', sa.Boolean(), server_default='0', nullable=False))


def downgrade() -> None:
    op.drop_column('alias', 'internal')
    op.alter_column("alias", "active", server_default=sa.text("0"))
