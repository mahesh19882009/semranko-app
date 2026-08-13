"""
Phase 14 — Add missing composite indexes for production performance

Revision ID: phase14_add_missing_indexes
Revises: phase12_keyword_soft_delete
Create Date: 2026-08-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'phase14_add_missing_indexes'
down_revision: Union[str, Sequence[str], None] = 'phase12_keyword_soft_delete'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.engine import Engine
    engine: Engine = op.get_bind()
    inspector = sa_inspect(engine)

    keyword_indexes = {idx["name"] for idx in inspector.get_indexes("Keyword")}
    if "idx_keyword_weekly_eligibility" not in keyword_indexes:
        op.create_index('idx_keyword_weekly_eligibility', 'Keyword', ['lastWeeklyRefreshAt', 'weeklyRefreshStatus', 'isActive'])
    if "idx_keyword_monthly_eligibility" not in keyword_indexes:
        op.create_index('idx_keyword_monthly_eligibility', 'Keyword', ['lastMonthlyMetricsRefreshAt', 'isActive'])
    if "idx_keyword_deleted_at" not in keyword_indexes:
        op.create_index('idx_keyword_deleted_at', 'Keyword', ['deletedAt'])

    ledger_indexes = {idx["name"] for idx in inspector.get_indexes("CreditLedger")}
    if "CreditLedger_projectId_idx" not in ledger_indexes:
        op.create_index('CreditLedger_projectId_idx', 'CreditLedger', ['projectId'])
    if "CreditLedger_keywordId_idx" not in ledger_indexes:
        op.create_index('CreditLedger_keywordId_idx', 'CreditLedger', ['keywordId'])
    if "idx_credit_ledger_user_timestamp_action" not in ledger_indexes:
        op.create_index('idx_credit_ledger_user_timestamp_action', 'CreditLedger', ['userId', 'timestamp', 'actionType'])

    dfs_indexes = {idx["name"] for idx in inspector.get_indexes("DataForSEOCost")}
    if "DataForSEOCost_taskId_idx" not in dfs_indexes:
        op.create_index('DataForSEOCost_taskId_idx', 'DataForSEOCost', ['taskId'])
    if "idx_dfs_user_created_at" not in dfs_indexes:
        op.create_index('idx_dfs_user_created_at', 'DataForSEOCost', ['userId', 'createdAt'])

    processing_indexes = {idx["name"] for idx in inspector.get_indexes("ProcessingJob")}
    if "ProcessingJob_deduplicationKey_idx" not in processing_indexes:
        op.create_index('ProcessingJob_deduplicationKey_idx', 'ProcessingJob', ['deduplicationKey'])
    if "ProcessingJob_processingTimeoutAt_idx" not in processing_indexes:
        op.create_index('ProcessingJob_processingTimeoutAt_idx', 'ProcessingJob', ['processingTimeoutAt'])


def downgrade() -> None:
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.engine import Engine
    engine: Engine = op.get_bind()
    inspector = sa_inspect(engine)

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("Keyword")}
    if "idx_keyword_weekly_eligibility" in existing_indexes:
        op.drop_index('idx_keyword_weekly_eligibility', table_name='Keyword')
    if "idx_keyword_monthly_eligibility" in existing_indexes:
        op.drop_index('idx_keyword_monthly_eligibility', table_name='Keyword')
    if "idx_keyword_deleted_at" in existing_indexes:
        op.drop_index('idx_keyword_deleted_at', table_name='Keyword')

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("CreditLedger")}
    for idx_name in ["CreditLedger_projectId_idx", "CreditLedger_keywordId_idx", "idx_credit_ledger_user_timestamp_action"]:
        if idx_name in existing_indexes:
            op.drop_index(idx_name, table_name='CreditLedger')

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("DataForSEOCost")}
    for idx_name in ["DataForSEOCost_taskId_idx", "idx_dfs_user_created_at"]:
        if idx_name in existing_indexes:
            op.drop_index(idx_name, table_name='DataForSEOCost')

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("ProcessingJob")}
    for idx_name in ["ProcessingJob_deduplicationKey_idx", "ProcessingJob_processingTimeoutAt_idx"]:
        if idx_name in existing_indexes:
            op.drop_index(idx_name, table_name='ProcessingJob')
