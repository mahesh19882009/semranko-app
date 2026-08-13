"""add lastMonthlyMetricsRefreshAt to keyword

Revision ID: b2c3d4e5f6a9
Revises: f1a2b3c4d5e6
Create Date: 2026-08-11 10:14:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a9'
down_revision: Union[str, Sequence[str], None] = 'b4aa091cafe5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('Keyword', sa.Column('lastMonthlyMetricsRefreshAt', sa.DateTime(), nullable=True))
    op.create_index('idx_keyword_last_monthly_metrics_refresh', 'Keyword', ['lastMonthlyMetricsRefreshAt'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_keyword_last_monthly_metrics_refresh', table_name='Keyword')
    op.drop_column('Keyword', 'lastMonthlyMetricsRefreshAt')
