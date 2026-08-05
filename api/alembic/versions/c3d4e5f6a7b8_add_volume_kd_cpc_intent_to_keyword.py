"""Add volume, kd, cpc, intent to Keyword

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-30 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('Keyword', sa.Column('volume', sa.Integer(), nullable=True))
    op.add_column('Keyword', sa.Column('kd', sa.Integer(), nullable=True))
    op.add_column('Keyword', sa.Column('cpc', sa.Float(), nullable=True))
    op.add_column('Keyword', sa.Column('intent', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('Keyword', 'intent')
    op.drop_column('Keyword', 'cpc')
    op.drop_column('Keyword', 'kd')
    op.drop_column('Keyword', 'volume')
