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
    from sqlalchemy import inspect as sa_inspect, text
    from sqlalchemy.engine import Engine
    engine: Engine = op.get_bind()
    inspector = sa_inspect(engine)

    keywordcache_columns = [c["name"] for c in inspector.get_columns("KeywordCache")]
    if "lastApiCallAt" not in keywordcache_columns:
        op.add_column('KeywordCache', sa.Column('lastApiCallAt', sa.DateTime(timezone=False), nullable=True))

    table_names = [t.lower() for t in inspector.get_table_names()]
    if "asynctaskqueue" not in table_names:
        with engine.connect() as conn:
            conn.execute(text('''
                CREATE TABLE "AsyncTaskQueue" (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    "taskId" VARCHAR,
                    "taskType" VARCHAR NOT NULL,
                    status VARCHAR DEFAULT 'pending' NOT NULL,
                    "keywordsJson" TEXT,
                    domain VARCHAR,
                    "locationCode" INTEGER,
                    device VARCHAR DEFAULT 'desktop',
                    "userId" VARCHAR,
                    "projectId" VARCHAR,
                    "resultJson" TEXT,
                    "errorMessage" TEXT,
                    "createdAt" TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
                    "updatedAt" TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
                    "completedAt" TIMESTAMP WITHOUT TIME ZONE
                )
            '''))
            conn.execute(text('CREATE INDEX IF NOT EXISTS "AsyncTaskQueue_status_idx" ON "AsyncTaskQueue" (status)'))
            conn.execute(text('CREATE INDEX IF NOT EXISTS "AsyncTaskQueue_taskType_idx" ON "AsyncTaskQueue" ("taskType")'))
            conn.execute(text('CREATE INDEX IF NOT EXISTS "AsyncTaskQueue_createdAt_idx" ON "AsyncTaskQueue" ("createdAt")'))
            conn.execute(text('CREATE INDEX IF NOT EXISTS "AsyncTaskQueue_taskId_idx" ON "AsyncTaskQueue" ("taskId")'))
            conn.commit()


def downgrade() -> None:
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.engine import Engine
    engine: Engine = op.get_bind()
    inspector = sa_inspect(engine)

    if "AsyncTaskQueue" in [t.lower() for t in inspector.get_table_names()]:
        op.drop_index('AsyncTaskQueue_taskId_idx', 'AsyncTaskQueue')
        op.drop_index('AsyncTaskQueue_createdAt_idx', 'AsyncTaskQueue')
        op.drop_index('AsyncTaskQueue_taskType_idx', 'AsyncTaskQueue')
        op.drop_index('AsyncTaskQueue_status_idx', 'AsyncTaskQueue')
        op.drop_table('AsyncTaskQueue')

    keywordcache_columns = [c["name"] for c in inspector.get_columns("KeywordCache")]
    if "lastApiCallAt" in keywordcache_columns:
        op.drop_column('KeywordCache', 'lastApiCallAt')
