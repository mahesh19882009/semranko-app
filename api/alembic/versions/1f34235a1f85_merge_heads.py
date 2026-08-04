"""merge heads

Revision ID: 1f34235a1f85
Revises: 466f73b9a093, f1a2b3c4d5e6
Create Date: 2026-08-03 22:39:29.765785

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f34235a1f85'
down_revision: Union[str, Sequence[str], None] = ('466f73b9a093', 'f1a2b3c4d5e6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
