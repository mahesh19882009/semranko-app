"""phase10_queue_based_refresh_architecture

Revision ID: f1a2b3c4d5e6
Revises: e5f6a7b8c9d0
Create Date: 2026-08-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.engine import Engine
    engine: Engine = op.get_bind()
    inspector = sa_inspect(engine)

    keyword_columns = [c["name"] for c in inspector.get_columns("Keyword")]
    if "processingTimeoutAt" not in keyword_columns:
        op.add_column('Keyword', sa.Column('processingTimeoutAt', sa.DateTime(), nullable=True))

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("Keyword")}
    if "idx_keyword_weekly_eligibility" not in existing_indexes:
        op.create_index('idx_keyword_weekly_eligibility', 'Keyword', ['lastWeeklyRefreshAt', 'weeklyRefreshStatus', 'isActive'])
    if "idx_keyword_monthly_eligibility" not in existing_indexes:
        op.create_index('idx_keyword_monthly_eligibility', 'Keyword', ['lastMonthlyMetricsRefreshAt', 'isActive'])

    if "RefreshJob" not in inspector.get_table_names():
        op.create_table(
            'RefreshJob',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('jobType', sa.String(), nullable=False),
            sa.Column('status', sa.String(), nullable=False, server_default='queued'),
            sa.Column('batchIndex', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('totalBatches', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('keywordCount', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('keywordsJson', sa.Text(), nullable=True),
            sa.Column('dataforseoRequestIds', sa.Text(), nullable=True),
            sa.Column('resultSummary', sa.Text(), nullable=True),
            sa.Column('retryCount', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('maxRetries', sa.Integer(), nullable=False, server_default='3'),
            sa.Column('processingTimeoutAt', sa.DateTime(), nullable=True),
            sa.Column('createdAt', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updatedAt', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('completedAt', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('RefreshJob_status_idx', 'RefreshJob', ['status'])
        op.create_index('RefreshJob_createdAt_idx', 'RefreshJob', ['createdAt'])
        op.create_index('RefreshJob_jobType_status_idx', 'RefreshJob', ['jobType', 'status'])

    if "ProcessingJob" not in inspector.get_table_names():
        op.create_table(
            'ProcessingJob',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('refreshJobId', sa.String(), nullable=False),
            sa.Column('keywordText', sa.String(), nullable=False),
            sa.Column('location', sa.String(), nullable=False),
            sa.Column('status', sa.String(), nullable=False, server_default='pending'),
            sa.Column('payload', sa.Text(), nullable=True),
            sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('createdAt', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updatedAt', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ProcessingJob_refreshJobId_idx', 'ProcessingJob', ['refreshJobId'])
        op.create_index('ProcessingJob_status_idx', 'ProcessingJob', ['status'])
        op.create_index('ProcessingJob_refreshJobId_status_idx', 'ProcessingJob', ['refreshJobId', 'status'])


def downgrade() -> None:
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.engine import Engine
    engine: Engine = op.get_bind()
    inspector = sa_inspect(engine)

    if "ProcessingJob" in inspector.get_table_names():
        op.drop_index('ProcessingJob_refreshJobId_status_idx', table_name='ProcessingJob')
        op.drop_index('ProcessingJob_status_idx', table_name='ProcessingJob')
        op.drop_index('ProcessingJob_refreshJobId_idx', table_name='ProcessingJob')
        op.drop_table('ProcessingJob')

    if "RefreshJob" in inspector.get_table_names():
        op.drop_index('RefreshJob_jobType_status_idx', table_name='RefreshJob')
        op.drop_index('RefreshJob_createdAt_idx', table_name='RefreshJob')
        op.drop_index('RefreshJob_status_idx', table_name='RefreshJob')
        op.drop_table('RefreshJob')

    keyword_columns = [c["name"] for c in inspector.get_columns("Keyword")]
    if "processingTimeoutAt" in keyword_columns:
        op.drop_column('Keyword', 'processingTimeoutAt')

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("Keyword")}
    if "idx_keyword_monthly_eligibility" in existing_indexes:
        op.drop_index('idx_keyword_monthly_eligibility', table_name='Keyword')
    if "idx_keyword_weekly_eligibility" in existing_indexes:
        op.drop_index('idx_keyword_weekly_eligibility', table_name='Keyword')
