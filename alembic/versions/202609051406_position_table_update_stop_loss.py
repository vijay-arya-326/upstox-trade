"""position_table_update--stop_loss

Revision ID: e27ced999ef1
Revises: b65e174e4e3b
Create Date: 2026-09-05 14:06:57.716703

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'e27ced999ef1'
down_revision: Union[str, Sequence[str], None] = 'b65e174e4e3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

table_name = "positions"
def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(table_name, sa.column("trigger_price", sa.Float(), nullable=False))
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column(table_name, "trigger_price")
    pass
