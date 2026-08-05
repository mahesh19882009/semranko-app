"""Add keyword list, competitor rank, keyword cluster, aio tracking

Revision ID: a1b2c3d4e5f6
Revises: c27c7b237d78
Create Date: 2026-07-30 08:37:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'c27c7b237d78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('KeywordList',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('userId', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('createdAt', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['userId'], ['User.id'], name='KeywordList_userId_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='KeywordList_pkey')
    )
    op.create_index('KeywordList_userId_idx', 'KeywordList', ['userId'], unique=False)

    op.create_table('KeywordListItem',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('listId', sa.String(), nullable=False),
    sa.Column('keyword', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['listId'], ['KeywordList.id'], name='KeywordListItem_listId_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='KeywordListItem_pkey')
    )
    op.create_index('KeywordListItem_listId_idx', 'KeywordListItem', ['listId'], unique=False)

    op.create_table('KeywordCluster',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('projectId', sa.String(), nullable=False),
    sa.Column('topic', sa.String(), nullable=False),
    sa.Column('keywords', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.Column('createdAt', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['projectId'], ['Project.id'], name='KeywordCluster_projectId_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='KeywordCluster_pkey')
    )
    op.create_index('KeywordCluster_projectId_idx', 'KeywordCluster', ['projectId'], unique=False)

    op.create_table('AIOTracking',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('projectId', sa.String(), nullable=False),
    sa.Column('keywordText', sa.String(), nullable=False),
    sa.Column('hasAIOverview', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    sa.Column('aiOverviewText', sa.Text(), nullable=True),
    sa.Column('citedDomains', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.Column('checkedAt', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['projectId'], ['Project.id'], name='AIOTracking_projectId_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='AIOTracking_pkey')
    )
    op.create_index('AIOTracking_projectId_idx', 'AIOTracking', ['projectId'], unique=False)
    op.create_index('AIOTracking_projectId_keyword_key', 'AIOTracking', ['projectId', 'keywordText'], unique=True)

    op.create_table('CompetitorRank',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('projectId', sa.String(), nullable=False),
    sa.Column('competitorId', sa.String(), nullable=False),
    sa.Column('keywordText', sa.String(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=True),
    sa.Column('url', sa.Text(), nullable=True),
    sa.Column('checkedAt', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['competitorId'], ['Competitor.id'], name='CompetitorRank_competitorId_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['projectId'], ['Project.id'], name='CompetitorRank_projectId_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='CompetitorRank_pkey')
    )
    op.create_index('CompetitorRank_projectId_idx', 'CompetitorRank', ['projectId'], unique=False)
    op.create_index('CompetitorRank_projectId_competitor_keyword_key', 'CompetitorRank', ['projectId', 'competitorId', 'keywordText'], unique=True)


def downgrade() -> None:
    op.drop_index('CompetitorRank_projectId_competitor_keyword_key', table_name='CompetitorRank')
    op.drop_index('CompetitorRank_projectId_idx', table_name='CompetitorRank')
    op.drop_table('CompetitorRank')
    op.drop_index('AIOTracking_projectId_keyword_key', table_name='AIOTracking')
    op.drop_index('AIOTracking_projectId_idx', table_name='AIOTracking')
    op.drop_table('AIOTracking')
    op.drop_index('KeywordCluster_projectId_idx', table_name='KeywordCluster')
    op.drop_table('KeywordCluster')
    op.drop_index('KeywordListItem_listId_idx', table_name='KeywordListItem')
    op.drop_table('KeywordListItem')
    op.drop_index('KeywordList_userId_idx', table_name='KeywordList')
    op.drop_table('KeywordList')
