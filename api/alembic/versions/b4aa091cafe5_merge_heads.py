"""merge heads

Revision ID: b4aa091cafe5
Revises: a8b9c0d1e2f3, aio_rankresult_extras, d1e2f3a4b5c6
Create Date: 2026-08-11 10:18:33.211872

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4aa091cafe5'
down_revision: Union[str, Sequence[str], None] = ('a8b9c0d1e2f3', 'aio_rankresult_extras', 'd1e2f3a4b5c6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
