"""add_dataforseo_and_ledger_tracking_fields

Revision ID: d1e2f3a4b5c6
Revises: c9d0e1f2a3b4
Create Date: 2026-08-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect as sa_inspect, text
    from sqlalchemy.engine import Engine
    engine: Engine = op.get_bind()
    inspector = sa_inspect(engine)

    dataforseo_columns = [c["name"] for c in inspector.get_columns("DataForSEOCost")]
    if "projectId" not in dataforseo_columns:
        op.add_column('DataForSEOCost', sa.Column('projectId', sa.String(), nullable=True))
    if "keywordId" not in dataforseo_columns:
        op.add_column('DataForSEOCost', sa.Column('keywordId', sa.String(), nullable=True))
    if "taskId" not in dataforseo_columns:
        op.add_column('DataForSEOCost', sa.Column('taskId', sa.String(), nullable=True))
    if "requestId" not in dataforseo_columns:
        op.add_column('DataForSEOCost', sa.Column('requestId', sa.String(), nullable=True))

    ledger_columns = [c["name"] for c in inspector.get_columns("CreditLedger")]
    if "projectId" not in ledger_columns:
        op.add_column('CreditLedger', sa.Column('projectId', sa.String(), nullable=True))
    if "keywordId" not in ledger_columns:
        op.add_column('CreditLedger', sa.Column('keywordId', sa.String(), nullable=True))
    if "creditsReserved" not in ledger_columns:
        op.add_column('CreditLedger', sa.Column('creditsReserved', sa.Float(), nullable=True))
    if "creditsConsumed" not in ledger_columns:
        op.add_column('CreditLedger', sa.Column('creditsConsumed', sa.Float(), nullable=True))
    if "creditsRefunded" not in ledger_columns:
        op.add_column('CreditLedger', sa.Column('creditsRefunded', sa.Float(), nullable=True))
    if "netCreditChange" not in ledger_columns:
        op.add_column('CreditLedger', sa.Column('netCreditChange', sa.Float(), nullable=True))
    if "balanceBefore" not in ledger_columns:
        op.add_column('CreditLedger', sa.Column('balanceBefore', sa.Float(), nullable=True))
    if "balanceAfter" not in ledger_columns:
        op.add_column('CreditLedger', sa.Column('balanceAfter', sa.Float(), nullable=True))
    if "taskId" not in ledger_columns:
        op.add_column('CreditLedger', sa.Column('taskId', sa.String(), nullable=True))
    if "requestId" not in ledger_columns:
        op.add_column('CreditLedger', sa.Column('requestId', sa.String(), nullable=True))


def downgrade() -> None:
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.engine import Engine
    engine: Engine = op.get_bind()
    inspector = sa_inspect(engine)

    dataforseo_columns = [c["name"] for c in inspector.get_columns("DataForSEOCost")]
    if "requestId" in dataforseo_columns:
        op.drop_column('DataForSEOCost', 'requestId')
    if "taskId" in dataforseo_columns:
        op.drop_column('DataForSEOCost', 'taskId')
    if "keywordId" in dataforseo_columns:
        op.drop_column('DataForSEOCost', 'keywordId')
    if "projectId" in dataforseo_columns:
        op.drop_column('DataForSEOCost', 'projectId')

    ledger_columns = [c["name"] for c in inspector.get_columns("CreditLedger")]
    if "requestId" in ledger_columns:
        op.drop_column('CreditLedger', 'requestId')
    if "taskId" in ledger_columns:
        op.drop_column('CreditLedger', 'taskId')
    if "balanceAfter" in ledger_columns:
        op.drop_column('CreditLedger', 'balanceAfter')
    if "balanceBefore" in ledger_columns:
        op.drop_column('CreditLedger', 'balanceBefore')
    if "netCreditChange" in ledger_columns:
        op.drop_column('CreditLedger', 'netCreditChange')
    if "creditsRefunded" in ledger_columns:
        op.drop_column('CreditLedger', 'creditsRefunded')
    if "creditsConsumed" in ledger_columns:
        op.drop_column('CreditLedger', 'creditsConsumed')
    if "creditsReserved" in ledger_columns:
        op.drop_column('CreditLedger', 'creditsReserved')
    if "keywordId" in ledger_columns:
        op.drop_column('CreditLedger', 'keywordId')
    if "projectId" in ledger_columns:
        op.drop_column('CreditLedger', 'projectId')
