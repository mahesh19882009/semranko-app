"""drop team tables

Revision ID: a1b2c3d4e5f7
Revises: f1a2b3c4d5e6
Create Date: 2026-08-09 16:46:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('DROP TABLE IF EXISTS "TeamMember" CASCADE')
    op.execute('DROP TABLE IF EXISTS "Team" CASCADE')


def downgrade() -> None:
    op.execute('''
        CREATE TABLE "Team" (
            id VARCHAR NOT NULL PRIMARY KEY,
            "ownerId" VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            "createdAt" DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP),
            FOREIGN KEY("ownerId") REFERENCES "User" (id) ON DELETE CASCADE
        )
    ''')
    op.execute('''
        CREATE TABLE "TeamMember" (
            id VARCHAR NOT NULL PRIMARY KEY,
            "teamId" VARCHAR NOT NULL,
            "userId" VARCHAR NOT NULL,
            role VARCHAR NOT NULL DEFAULT 'Viewer',
            "joinedAt" DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP),
            FOREIGN KEY("teamId") REFERENCES "Team" (id) ON DELETE CASCADE,
            FOREIGN KEY("userId") REFERENCES "User" (id) ON DELETE CASCADE,
            UNIQUE ("teamId", "userId")
        )
    ''')
    op.execute('CREATE INDEX "TeamMember_teamId_idx" ON "TeamMember" ("teamId")')
    op.execute('CREATE INDEX "TeamMember_userId_idx" ON "TeamMember" ("userId")')
