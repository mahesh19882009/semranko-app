from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, Sequence[str], None] = 'a54a6d764a82'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('Keyword', sa.Column('competition', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('Keyword', 'competition')
