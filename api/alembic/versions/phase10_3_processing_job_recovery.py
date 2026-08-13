"""phase10_3_processing_job_recovery

Revision ID: phase10_3_processing_job_recovery
Revises: a1b2c3d4e5f6
Create Date: 2026-08-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'phase10_3_processing_job_recovery'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.engine import Engine
    engine: Engine = op.get_bind()
    inspector = sa_inspect(engine)

    processing_job_columns = [c["name"] for c in inspector.get_columns("ProcessingJob")]
    
    if "processingTimeoutAt" not in processing_job_columns:
        op.add_column('ProcessingJob', sa.Column('processingTimeoutAt', sa.DateTime(), nullable=True))
    
    if "retryCount" not in processing_job_columns:
        op.add_column('ProcessingJob', sa.Column('retryCount', sa.Integer(), nullable=False, server_default='0'))
    
    if "maxRetries" not in processing_job_columns:
        op.add_column('ProcessingJob', sa.Column('maxRetries', sa.Integer(), nullable=False, server_default='3'))

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("ProcessingJob")}
    if "ProcessingJob_processingTimeoutAt_idx" not in existing_indexes:
        op.create_index('ProcessingJob_processingTimeoutAt_idx', 'ProcessingJob', ['processingTimeoutAt'])


def downgrade() -> None:
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.engine import Engine
    engine: Engine = op.get_bind()
    inspector = sa_inspect(engine)

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("ProcessingJob")}
    if "ProcessingJob_processingTimeoutAt_idx" in existing_indexes:
        op.drop_index('ProcessingJob_processingTimeoutAt_idx', table_name='ProcessingJob')

    processing_job_columns = [c["name"] for c in inspector.get_columns("ProcessingJob")]
    if "maxRetries" in processing_job_columns:
        op.drop_column('ProcessingJob', 'maxRetries')
    if "retryCount" in processing_job_columns:
        op.drop_column('ProcessingJob', 'retryCount')
    if "processingTimeoutAt" in processing_job_columns:
        op.drop_column('ProcessingJob', 'processingTimeoutAt')
