"""simplify aio: add ai_description to Keyword, drop AIOTracking

Revision ID: b2c3d4e5f6a8
Revises: f1a2b3c4d5e6
Create Date: 2026-08-09 20:50:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a8'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('ALTER TABLE "Keyword" ADD COLUMN IF NOT EXISTS "ai_description" TEXT')
    op.execute('DROP TABLE IF EXISTS "AIOTracking" CASCADE')


def downgrade() -> None:
    op.execute('''
        CREATE TABLE "AIOTracking" (
            id VARCHAR NOT NULL PRIMARY KEY,
            "projectId" VARCHAR NOT NULL,
            "keywordText" VARCHAR NOT NULL,
            "hasAIOverview" BOOLEAN NOT NULL DEFAULT FALSE,
            "aiOverviewText" TEXT,
            "aiOverviewTitle" VARCHAR,
            "aiOverviewMarkdown" TEXT,
            references JSON,
            images JSON,
            "aiOverviewType" VARCHAR,
            "citedDomains" JSON,
            "checkedAt" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY("projectId") REFERENCES "Project" (id) ON DELETE CASCADE,
            UNIQUE ("projectId", "keywordText")
        )
    ''')
    op.execute('CREATE INDEX IF NOT EXISTS "AIOTracking_projectId_idx" ON "AIOTracking" ("projectId")')
    op.execute('ALTER TABLE "Keyword" DROP COLUMN IF EXISTS "ai_description"')
