"""add_aio_tracking_fields_and_rankresult_etv

Revision ID: aio_rankresult_extras
Revises: 1f34235a1f85
Create Date: 2026-08-07 14:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'aio_rankresult_extras'
down_revision: Union[str, Sequence[str], None] = '1f34235a1f85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect as sa_inspect, text
    from sqlalchemy.engine import Engine
    engine: Engine = op.get_bind()
    inspector = sa_inspect(engine)
    table_names = [name.lower() for name in inspector.get_table_names()]

    if "aiotracking" in table_names:
        op.add_column('AIOTracking', sa.Column('aiOverviewTitle', sa.String(), nullable=True))
        op.add_column('AIOTracking', sa.Column('aiOverviewMarkdown', sa.Text(), nullable=True))
        op.add_column('AIOTracking', sa.Column('references', postgresql.JSON(astext_type=sa.Text()), nullable=True))
        op.add_column('AIOTracking', sa.Column('images', postgresql.JSON(astext_type=sa.Text()), nullable=True))
        op.add_column('AIOTracking', sa.Column('aiOverviewType', sa.String(), nullable=True))

    rankresult_columns = [c["name"] for c in inspector.get_columns("RankResult")]
    if "etv" not in rankresult_columns:
        op.add_column('RankResult', sa.Column('etv', sa.Float(), nullable=True))

    rankresult_indexes = [c["name"] for c in inspector.get_indexes("RankResult")]
    if "RankResult_projectId_keywordId_checkedAt_idx" not in rankresult_indexes:
        op.create_index('RankResult_projectId_keywordId_checkedAt_idx', 'RankResult', ['projectId', 'keywordId', 'checkedAt'])

    keyword_columns = [c["name"] for c in inspector.get_columns("Keyword")]
    if "visibility" not in keyword_columns:
        op.add_column('Keyword', sa.Column('visibility', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('Keyword', 'visibility')
    op.drop_index('RankResult_projectId_keywordId_checkedAt_idx', table_name='RankResult')
    op.drop_column('RankResult', 'etv')
    op.drop_column('AIOTracking', 'aiOverviewType')
    op.drop_column('AIOTracking', 'images')
    op.drop_column('AIOTracking', 'references')
    op.drop_column('AIOTracking', 'aiOverviewMarkdown')
    op.drop_column('AIOTracking', 'aiOverviewTitle')
