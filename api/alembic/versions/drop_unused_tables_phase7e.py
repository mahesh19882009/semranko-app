from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'drop_unused_tables_phase7e'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('ScheduledReport')
    op.drop_table('UserCacheUnlock')


def downgrade() -> None:
    op.create_table(
        'ScheduledReport',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('userId', sa.String(), nullable=False),
        sa.Column('projectId', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('frequency', sa.String(), nullable=False),
        sa.Column('format', sa.String(), nullable=False),
        sa.Column('recipients', sa.String(), nullable=False),
        sa.Column('startDate', sa.DateTime(), nullable=True),
        sa.Column('isActive', sa.Boolean(), nullable=False),
        sa.Column('lastSentAt', sa.DateTime(), nullable=True),
        sa.Column('nextSendAt', sa.DateTime(), nullable=True),
        sa.Column('createdAt', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['projectId'], ['Project.id'], name='ScheduledReport_projectId_fkey', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['userId'], ['User.id'], name='ScheduledReport_userId_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='ScheduledReport_pkey')
    )
    op.create_index('ScheduledReport_projectId_idx', 'ScheduledReport', ['projectId'], unique=False)
    op.create_index('ScheduledReport_userId_idx', 'ScheduledReport', ['userId'], unique=False)

    op.create_table(
        'UserCacheUnlock',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('ownerId', sa.String(), nullable=False),
        sa.Column('targetString', sa.String(), nullable=False),
        sa.Column('unlockedAt', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['ownerId'], ['User.id'], name='UserCacheUnlock_ownerId_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='UserCacheUnlock_pkey')
    )
    op.create_index('UserCacheUnlock_ownerId_idx', 'UserCacheUnlock', ['ownerId'], unique=False)
    op.create_index('UserCacheUnlock_ownerId_targetString_key', 'UserCacheUnlock', ['ownerId', 'targetString'], unique=True)
