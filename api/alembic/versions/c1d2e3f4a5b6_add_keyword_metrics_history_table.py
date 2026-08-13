"""add_keyword_metrics_history_table

Revision ID: c1d2e3f4a5b6
Revises: b2c3d4e5f6a9
Create Date: 2026-08-11 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'KeywordMetricsHistory',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('keywordId', sa.String(), nullable=False),
        sa.Column('projectId', sa.String(), nullable=False),
        sa.Column('userId', sa.String(), nullable=False),
        sa.Column('volume', sa.Integer(), nullable=True),
        sa.Column('kd', sa.Integer(), nullable=True),
        sa.Column('cpc', sa.Float(), nullable=True),
        sa.Column('competition', sa.Float(), nullable=True),
        sa.Column('backlinks', sa.Float(), nullable=True),
        sa.Column('referring_domains', sa.Float(), nullable=True),
        sa.Column('intent', sa.String(), nullable=True),
        sa.Column('refreshedAt', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['keywordId'], ['Keyword.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['projectId'], ['Project.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['userId'], ['User.id'], ondelete='CASCADE'),
    )
    op.create_index('KeywordMetricsHistory_keywordId_refreshedAt_idx', 'KeywordMetricsHistory', ['keywordId', 'refreshedAt'])
    op.create_index('KeywordMetricsHistory_projectId_refreshedAt_idx', 'KeywordMetricsHistory', ['projectId', 'refreshedAt'])


def downgrade() -> None:
    op.drop_index('KeywordMetricsHistory_projectId_refreshedAt_idx', table_name='KeywordMetricsHistory')
    op.drop_index('KeywordMetricsHistory_keywordId_refreshedAt_idx', table_name='KeywordMetricsHistory')
    op.drop_table('KeywordMetricsHistory')
