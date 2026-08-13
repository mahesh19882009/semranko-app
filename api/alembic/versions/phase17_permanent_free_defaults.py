"""Make database defaults consistent with the permanent Free lifecycle.

Revision ID: phase17_permanent_free_defaults
Revises: phase16_auto_credits
"""

from alembic import op
import sqlalchemy as sa


revision = "phase17_permanent_free_defaults"
down_revision = "phase16_auto_credits"
branch_labels = None
depends_on = None


def upgrade():
    # Registration already sets these values explicitly. These defaults protect
    # direct database inserts and future creation paths from granting Starter
    # entitlement or reviving the obsolete trial lifecycle.
    op.alter_column(
        "User", "selectedPlan", existing_type=sa.String(),
        server_default=sa.text("'free_trial'"),
    )
    op.alter_column(
        "User", "subscriptionStatus", existing_type=sa.String(),
        server_default=sa.text("'free'"),
    )


def downgrade():
    op.alter_column(
        "User", "subscriptionStatus", existing_type=sa.String(),
        server_default=sa.text("'trialing'"),
    )
    op.alter_column(
        "User", "selectedPlan", existing_type=sa.String(),
        server_default=sa.text("'starter'"),
    )
