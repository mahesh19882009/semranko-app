"""
Phase 12 — Add deletedAt column to Keyword for soft-delete cooldown tracking

Revision ID: phase12_keyword_soft_delete
Revises: phase12_mobile_verification
Create Date: 2026-08-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'phase12_keyword_soft_delete'
down_revision: Union[str, Sequence[str], None] = 'phase12_mobile_verification'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.engine import Engine
    engine: Engine = op.get_bind()
    inspector = sa_inspect(engine)

    keyword_columns = [c["name"] for c in inspector.get_columns("Keyword")]
    
    if "deletedAt" not in keyword_columns:
        op.add_column('Keyword', sa.Column('deletedAt', sa.DateTime(), nullable=True))

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("Keyword")}
    if "idx_keyword_deleted_at" not in existing_indexes:
        op.create_index('idx_keyword_deleted_at', 'Keyword', ['deletedAt'])


def downgrade() -> None:
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.engine import Engine
    engine: Engine = op.get_bind()
    inspector = sa_inspect(engine)

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("Keyword")}
    if "idx_keyword_deleted_at" in existing_indexes:
        op.drop_index('idx_keyword_deleted_at', table_name='Keyword')

    keyword_columns = [c["name"] for c in inspector.get_columns("Keyword")]
    if "deletedAt" in keyword_columns:
        op.drop_column('Keyword', 'deletedAt')
