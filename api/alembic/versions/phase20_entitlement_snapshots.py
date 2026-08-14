"""Immutable commercial entitlement snapshots per billing cycle.

Revision ID: phase20_entitlement_snapshots
Revises: phase19_commercial_configuration
"""
from alembic import op
import sqlalchemy as sa

revision = "phase20_entitlement_snapshots"
down_revision = "phase19_commercial_configuration"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("SubscriptionEntitlementSnapshot",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("userId", sa.String(), sa.ForeignKey("User.id", ondelete="CASCADE"), nullable=False),
        sa.Column("planKey", sa.String(), nullable=False), sa.Column("cycleStart", sa.DateTime(), nullable=False), sa.Column("cycleEnd", sa.DateTime()),
        sa.Column("projectLimit", sa.Integer(), nullable=False), sa.Column("keywordLimit", sa.Integer(), nullable=False),
        sa.Column("monthlyCredits", sa.Integer(), nullable=False), sa.Column("automaticCredits", sa.Integer(), nullable=False),
        sa.Column("manualRefreshLimit", sa.Integer(), nullable=False), sa.Column("keywordResearchLimit", sa.Integer(), nullable=False), sa.Column("competitorSpyLimit", sa.Integer(), nullable=False),
        sa.Column("createdAt", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('"automaticCredits" >= 0 AND "automaticCredits" <= "monthlyCredits"', name="snapshot_automatic_valid"),
    )
    op.create_index("entitlement_snapshot_user_cycle_key", "SubscriptionEntitlementSnapshot", ["userId", "cycleStart"], unique=True)
    # Preserve exactly the editable entitlement values enforced by the
    # pre-Phase-20 in-memory definitions, even if Phase-19 offerings were edited.
    op.execute(sa.text('''
        INSERT INTO "SubscriptionEntitlementSnapshot"
            (id, "userId", "planKey", "cycleStart", "cycleEnd", "projectLimit", "keywordLimit",
             "monthlyCredits", "automaticCredits", "manualRefreshLimit", "keywordResearchLimit", "competitorSpyLimit")
        SELECT 'snapshot-legacy-' || id, id,
            CASE WHEN LOWER(TRIM(COALESCE("selectedPlan", ''))) IN ('starter','pro','agency')
                 THEN LOWER(TRIM("selectedPlan")) ELSE 'free_trial' END,
            COALESCE("lastCreditResetAt", "planAnniversaryAt", "createdAt", CURRENT_TIMESTAMP), NULL,
            CASE LOWER(TRIM(COALESCE("selectedPlan", ''))) WHEN 'starter' THEN 1 WHEN 'pro' THEN 5 WHEN 'agency' THEN 20 ELSE 1 END,
            CASE LOWER(TRIM(COALESCE("selectedPlan", ''))) WHEN 'starter' THEN 100 WHEN 'pro' THEN 500 WHEN 'agency' THEN 1500 ELSE 5 END,
            CASE LOWER(TRIM(COALESCE("selectedPlan", ''))) WHEN 'starter' THEN 8000 WHEN 'pro' THEN 40000 WHEN 'agency' THEN 120000 ELSE 100 END,
            CASE LOWER(TRIM(COALESCE("selectedPlan", ''))) WHEN 'starter' THEN 5000 WHEN 'pro' THEN 25000 WHEN 'agency' THEN 75000 ELSE 0 END,
            CASE LOWER(TRIM(COALESCE("selectedPlan", ''))) WHEN 'starter' THEN 10 WHEN 'pro' THEN 50 WHEN 'agency' THEN 150 ELSE 0 END,
            CASE LOWER(TRIM(COALESCE("selectedPlan", ''))) WHEN 'starter' THEN 10 WHEN 'pro' THEN 30 WHEN 'agency' THEN 75 ELSE 0 END,
            CASE LOWER(TRIM(COALESCE("selectedPlan", ''))) WHEN 'starter' THEN 3 WHEN 'pro' THEN 10 WHEN 'agency' THEN 25 ELSE 0 END
        FROM "User"
    '''))

def downgrade():
    op.drop_index("entitlement_snapshot_user_cycle_key", table_name="SubscriptionEntitlementSnapshot")
    op.drop_table("SubscriptionEntitlementSnapshot")
