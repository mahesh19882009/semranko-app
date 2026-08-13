"""phase10_1_production_hardening_idempotency

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-08-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.engine import Engine
    engine: Engine = op.get_bind()
    inspector = sa_inspect(engine)

    processing_job_columns = [c["name"] for c in inspector.get_columns("ProcessingJob")]
    if "deduplicationKey" not in processing_job_columns:
        op.add_column('ProcessingJob', sa.Column('deduplicationKey', sa.String(), nullable=False, server_default=''))
        op.alter_column('ProcessingJob', 'deduplicationKey', server_default=None)

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("ProcessingJob")}
    if "ProcessingJob_deduplicationKey_idx" not in existing_indexes:
        op.create_index('ProcessingJob_deduplicationKey_idx', 'ProcessingJob', ['deduplicationKey'], unique=True)


def downgrade() -> None:
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.engine import Engine
    engine: Engine = op.get_bind()
    inspector = sa_inspect(engine)

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("ProcessingJob")}
    if "ProcessingJob_deduplicationKey_idx" in existing_indexes:
        op.drop_index('ProcessingJob_deduplicationKey_idx', table_name='ProcessingJob')

    processing_job_columns = [c["name"] for c in inspector.get_columns("ProcessingJob")]
    if "deduplicationKey" in processing_job_columns:
        op.drop_column('ProcessingJob', 'deduplicationKey')
