"""Persist exact Keyword identity on user-triggered processing children."""

from alembic import op
import sqlalchemy as sa


revision = "phase22_job_keyword_id"
down_revision = "phase21_keyword_target_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ProcessingJob",
        sa.Column("keywordId", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "ProcessingJob_keywordId_fkey",
        "ProcessingJob",
        "Keyword",
        ["keywordId"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ProcessingJob_keywordId_idx",
        "ProcessingJob",
        ["keywordId"],
    )


def downgrade() -> None:
    op.drop_index("ProcessingJob_keywordId_idx", table_name="ProcessingJob")
    op.drop_constraint(
        "ProcessingJob_keywordId_fkey",
        "ProcessingJob",
        type_="foreignkey",
    )
    op.drop_column("ProcessingJob", "keywordId")
