"""filled_qty

Revision ID: 1fd78598cb2d
Revises: d503bf1cf637
Create Date: 2026-09-02 14:12:14.224571

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '1fd78598cb2d'
down_revision: Union[str, Sequence[str], None] = 'd503bf1cf637'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("order_details", sa.Column("filled_qty", sa.Integer(), nullable=True))
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("order_details", "filled_qty")
    pass
