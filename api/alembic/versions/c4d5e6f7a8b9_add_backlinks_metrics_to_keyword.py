from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, Sequence[str], None] = 'b3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('Keyword', sa.Column('backlinks', sa.Float(), nullable=True))
    op.add_column('Keyword', sa.Column('referring_domains', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('Keyword', 'referring_domains')
    op.drop_column('Keyword', 'backlinks')
