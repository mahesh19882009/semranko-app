"""add_async_task_queue_and_cache_fields

Revision ID: a8b9c0d1e2f3
Revises: f1a2b3c4d5e6
Create Date: 2025-01-15

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a8b9c0d1e2f3'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add lastApiCallAt to KeywordCache table
    op.add_column('KeywordCache', sa.Column('lastApiCallAt', sa.DateTime(timezone=False), nullable=True))
    
    # Create AsyncTaskQueue table
    op.create_table('AsyncTaskQueue',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('taskId', sa.String(), nullable=True),
        sa.Column('taskType', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('keywordsJson', sa.Text(), nullable=True),
        sa.Column('domain', sa.String(), nullable=True),
        sa.Column('locationCode', sa.Integer(), nullable=True),
        sa.Column('device', sa.String(), nullable=True, server_default='desktop'),
        sa.Column('userId', sa.String(), nullable=True),
        sa.Column('projectId', sa.String(), nullable=True),
        sa.Column('resultJson', sa.Text(), nullable=True),
        sa.Column('errorMessage', sa.Text(), nullable=True),
        sa.Column('createdAt', sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.Column('updatedAt', sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.Column('completedAt', sa.DateTime(timezone=False), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for AsyncTaskQueue
    op.create_index('AsyncTaskQueue_status_idx', 'AsyncTaskQueue', ['status'])
    op.create_index('AsyncTaskQueue_taskType_idx', 'AsyncTaskQueue', ['taskType'])
    op.create_index('AsyncTaskQueue_createdAt_idx', 'AsyncTaskQueue', ['createdAt'])
    op.create_index('AsyncTaskQueue_taskId_idx', 'AsyncTaskQueue', ['taskId'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('AsyncTaskQueue_taskId_idx', 'AsyncTaskQueue')
    op.drop_index('AsyncTaskQueue_createdAt_idx', 'AsyncTaskQueue')
    op.drop_index('AsyncTaskQueue_taskType_idx', 'AsyncTaskQueue')
    op.drop_index('AsyncTaskQueue_status_idx', 'AsyncTaskQueue')
    
    # Drop AsyncTaskQueue table
    op.drop_table('AsyncTaskQueue')
    
    # Remove lastApiCallAt from KeywordCache
    op.drop_column('KeywordCache', 'lastApiCallAt')
