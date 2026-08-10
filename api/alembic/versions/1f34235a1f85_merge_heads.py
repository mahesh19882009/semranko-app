"""merge aio heads

Revision ID: 1f34235a1f85
Revises: 466f73b9a093, f1a2b3c4d5e6
Create Date: 2026-08-05 16:46:00.000000

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '1f34235a1f85'
down_revision: Union[str, Sequence[str], None] = ('466f73b9a093', 'f1a2b3c4d5e6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
