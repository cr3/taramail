"""Backend views

Revision ID: 8d3df567c75c
Revises: a465e415e03d
Create Date: 2025-02-01 21:19:15.965541

"""

from collections.abc import Sequence

from alembic import op
from taramail.views import (
    GroupedDomainAliasAddressView,
    GroupedMailAliasesView,
    GroupedSenderAclExternalView,
    GroupedSenderAclView,
)

# revision identifiers, used by Alembic.
revision: str = "8d3df567c75c"
down_revision: str | None = "a465e415e03d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    GroupedDomainAliasAddressView.create(op)
    GroupedMailAliasesView.create(op)
    GroupedSenderAclExternalView.create(op)
    GroupedSenderAclView.create(op)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    GroupedDomainAliasAddressView.drop(op)
    GroupedMailAliasesView.drop(op)
    GroupedSenderAclExternalView.drop(op)
    GroupedSenderAclView.drop(op)
    # ### end Alembic commands ###
