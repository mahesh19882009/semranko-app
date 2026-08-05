from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a54a6d764a82'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('TeamInvite')
    op.drop_table('TeamMember')
    op.drop_table('Team')
    op.drop_table('ApiKey')
    op.drop_table('Backlink')
    op.drop_table('Notification')
    op.drop_table('Report')
    op.drop_table('AuditIssue')
    op.drop_table('Audit')


def downgrade() -> None:
    op.create_table('Audit',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('projectId', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('score', sa.Integer(), nullable=False),
    sa.Column('totalIssues', sa.Integer(), nullable=False),
    sa.Column('criticalIssues', sa.Integer(), nullable=False),
    sa.Column('warningIssues', sa.Integer(), nullable=False),
    sa.Column('passedChecks', sa.Integer(), nullable=False),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('createdAt', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['projectId'], ['Project.id'], name='Audit_projectId_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='Audit_pkey')
    )
    op.create_index('Audit_projectId_idx', 'Audit', ['projectId'], unique=False)

    op.create_table('AuditIssue',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('auditId', sa.String(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('category', sa.String(), nullable=False),
    sa.Column('severity', sa.String(), nullable=False),
    sa.Column('recommendation', sa.Text(), nullable=False),
    sa.Column('createdAt', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['auditId'], ['Audit.id'], name='AuditIssue_auditId_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='AuditIssue_pkey')
    )
    op.create_index('AuditIssue_auditId_idx', 'AuditIssue', ['auditId'], unique=False)

    op.create_table('Report',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('projectId', sa.String(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('period', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('visibilityScore', sa.Integer(), nullable=False),
    sa.Column('keywordCount', sa.Integer(), nullable=False),
    sa.Column('top10Count', sa.Integer(), nullable=False),
    sa.Column('competitorCount', sa.Integer(), nullable=False),
    sa.Column('createdAt', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updatedAt', postgresql.TIMESTAMP(), nullable=False),
    sa.ForeignKeyConstraint(['projectId'], ['Project.id'], name='Report_projectId_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='Report_pkey')
    )
    op.create_index('Report_projectId_idx', 'Report', ['projectId'], unique=False)

    op.create_table('Notification',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('userId', sa.String(), nullable=False),
    sa.Column('projectId', sa.String(), nullable=True),
    sa.Column('type', sa.String(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('severity', sa.String(), nullable=False),
    sa.Column('entityType', sa.String(), nullable=True),
    sa.Column('entityId', sa.String(), nullable=True),
    sa.Column('payload', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.Column('readAt', postgresql.TIMESTAMP(), nullable=True),
    sa.Column('createdAt', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updatedAt', postgresql.TIMESTAMP(), nullable=False),
    sa.ForeignKeyConstraint(['userId'], ['User.id'], name='Notification_userId_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['projectId'], ['Project.id'], name='Notification_projectId_fkey', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name='Notification_pkey')
    )
    op.create_index('notification_user_id_idx', 'Notification', ['userId'], unique=False)
    op.create_index('notification_project_id_idx_v2', 'Notification', ['projectId'], unique=False)
    op.create_index('notification_status_idx', 'Notification', ['status'], unique=False)
    op.create_index('notification_created_at_idx', 'Notification', ['createdAt'], unique=False)

    op.create_table('Backlink',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('projectId', sa.String(), nullable=False),
    sa.Column('sourceUrl', sa.Text(), nullable=False),
    sa.Column('sourceDomain', sa.String(), nullable=False),
    sa.Column('anchor', sa.Text(), nullable=True),
    sa.Column('domainRank', sa.Integer(), nullable=True),
    sa.Column('firstSeen', postgresql.TIMESTAMP(), nullable=True),
    sa.Column('checkedAt', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['projectId'], ['Project.id'], name='Backlink_projectId_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='Backlink_pkey')
    )
    op.create_index('Backlink_projectId_idx', 'Backlink', ['projectId'], unique=False)

    op.create_table('ApiKey',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('userId', sa.String(), nullable=False),
    sa.Column('key', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('isActive', sa.Boolean(), nullable=False),
    sa.Column('lastUsed', postgresql.TIMESTAMP(), nullable=True),
    sa.Column('createdAt', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.Column('expiresAt', postgresql.TIMESTAMP(), nullable=True),
    sa.ForeignKeyConstraint(['userId'], ['User.id'], name='ApiKey_userId_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='ApiKey_pkey')
    )
    op.create_index('ApiKey_userId_idx', 'ApiKey', ['userId'], unique=False)
    op.create_index('ApiKey_key_idx', 'ApiKey', ['key'], unique=True)

    op.create_table('Team',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('ownerId', sa.String(), nullable=False),
    sa.Column('createdAt', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['ownerId'], ['User.id'], name='Team_ownerId_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='Team_pkey')
    )
    op.create_index('Team_ownerId_idx', 'Team', ['ownerId'], unique=False)

    op.create_table('TeamMember',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('teamId', sa.String(), nullable=False),
    sa.Column('userId', sa.String(), nullable=False),
    sa.Column('role', sa.String(), nullable=False),
    sa.Column('joinedAt', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['teamId'], ['Team.id'], name='TeamMember_teamId_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['userId'], ['User.id'], name='TeamMember_userId_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='TeamMember_pkey')
    )
    op.create_index('TeamMember_teamId_idx', 'TeamMember', ['teamId'], unique=False)
    op.create_index('TeamMember_userId_idx', 'TeamMember', ['userId'], unique=False)
    op.create_index('TeamMember_team_user_key', 'TeamMember', ['teamId', 'userId'], unique=True)

    op.create_table('TeamInvite',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('teamId', sa.String(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('role', sa.String(), nullable=False),
    sa.Column('invitedBy', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('expiresAt', postgresql.TIMESTAMP(), nullable=False),
    sa.Column('createdAt', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['teamId'], ['Team.id'], name='TeamInvite_teamId_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['invitedBy'], ['User.id'], name='TeamInvite_invitedBy_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='TeamInvite_pkey')
    )
    op.create_index('TeamInvite_teamId_idx', 'TeamInvite', ['teamId'], unique=False)
    op.create_index('TeamInvite_email_idx', 'TeamInvite', ['email'], unique=False)
    op.create_index('TeamInvite_status_idx', 'TeamInvite', ['status'], unique=False)