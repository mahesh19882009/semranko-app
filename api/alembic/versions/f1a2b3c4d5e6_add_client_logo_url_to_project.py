"""add client_logo_url to project

Revision ID: f1a2b3c4d5e6
Revises: e4bb19a5ac78
Create Date: 2026-08-03 20:53:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'e4bb19a5ac78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('Project', sa.Column('client_logo_url', sa.String(500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('Project', 'client_logo_url')
