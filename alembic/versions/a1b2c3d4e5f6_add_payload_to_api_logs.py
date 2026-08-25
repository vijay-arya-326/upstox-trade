"""add payload to api_logs

Revision ID: a1b2c3d4e5f6
Revises: 9f56575d1bbe
Create Date: 2026-08-25 15:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "9f56575d1bbe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("api_logs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("payload", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("api_logs", schema=None) as batch_op:
        batch_op.drop_column("payload")
