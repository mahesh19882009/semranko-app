"""add_weekly_refresh_tracking_to_keyword

Revision ID: e5f6a7b8c9d0
Revises: d1e2f3a4b5c6
Create Date: 2026-08-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.engine import Engine
    engine: Engine = op.get_bind()
    inspector = sa_inspect(engine)

    keyword_columns = [c["name"] for c in inspector.get_columns("Keyword")]
    if "lastWeeklyRefreshAt" not in keyword_columns:
        op.add_column('Keyword', sa.Column('lastWeeklyRefreshAt', sa.DateTime(), nullable=True))
    if "weeklyRefreshStatus" not in keyword_columns:
        op.add_column('Keyword', sa.Column('weeklyRefreshStatus', sa.String(), nullable=True))


def downgrade() -> None:
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.engine import Engine
    engine: Engine = op.get_bind()
    inspector = sa_inspect(engine)

    keyword_columns = [c["name"] for c in inspector.get_columns("Keyword")]
    if "weeklyRefreshStatus" in keyword_columns:
        op.drop_column('Keyword', 'weeklyRefreshStatus')
    if "lastWeeklyRefreshAt" in keyword_columns:
        op.drop_column('Keyword', 'lastWeeklyRefreshAt')
