"""Default alias private and public comments to empty

Revision ID: 688be1178ef6
Revises: 79d64ba432c7
Create Date: 2025-11-17 20:56:32.346864

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '688be1178ef6'
down_revision: str | None = '79d64ba432c7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE alias SET private_comment = '' WHERE private_comment IS NULL")
    op.execute("UPDATE alias SET public_comment = '' WHERE public_comment IS NULL")
    op.alter_column('alias', 'private_comment',
               existing_type=mysql.TEXT(),
               type_=sa.String(length=160),
               nullable=False,
               server_default="")
    op.alter_column('alias', 'public_comment',
               existing_type=mysql.TEXT(),
               type_=sa.String(length=160),
               nullable=False,
               server_default="")


def downgrade() -> None:
    op.alter_column('alias', 'public_comment',
               existing_type=sa.String(length=160),
               type_=mysql.TEXT(),
               nullable=True,
               server_default=None)
    op.alter_column('alias', 'private_comment',
               existing_type=sa.String(length=160),
               type_=mysql.TEXT(),
               nullable=True,
               server_default=None)
    op.execute("UPDATE alias SET public_comment = NULL WHERE public_comment = ''")
    op.execute("UPDATE alias SET private_comment = NULL WHERE private_comment = ''")
