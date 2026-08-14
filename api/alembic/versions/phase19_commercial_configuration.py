"""Database-backed commercial configuration and auditable top-up packages.

Revision ID: phase19_commercial_configuration
Revises: phase18_payment_order_billing_cycle
"""

from alembic import op
import sqlalchemy as sa


revision = "phase19_commercial_configuration"
down_revision = "phase18_payment_order_billing_cycle"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("User", sa.Column("isAdmin", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table(
        "PlanCommercialConfig",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("planKey", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=False), sa.Column("monthlyPriceInr", sa.Float(), nullable=False),
        sa.Column("monthlyPriceUsd", sa.Float(), nullable=False), sa.Column("projectLimit", sa.Integer(), nullable=False),
        sa.Column("keywordLimit", sa.Integer(), nullable=False), sa.Column("monthlyCredits", sa.Integer(), nullable=False),
        sa.Column("automaticCredits", sa.Integer(), nullable=False), sa.Column("manualRefreshLimit", sa.Integer(), nullable=False),
        sa.Column("keywordResearchLimit", sa.Integer(), nullable=False), sa.Column("competitorSpyLimit", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("createdAt", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("updatedAt", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('"monthlyPriceInr" >= 0'), sa.CheckConstraint('"monthlyPriceUsd" >= 0'),
        sa.CheckConstraint('"projectLimit" >= 0'), sa.CheckConstraint('"keywordLimit" >= 0'),
        sa.CheckConstraint('"monthlyCredits" >= 0'), sa.CheckConstraint('"automaticCredits" >= 0 AND "automaticCredits" <= "monthlyCredits"'),
    )
    op.create_table(
        "TopUpPackage",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("name", sa.String(), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False), sa.Column("priceInr", sa.Float(), nullable=False), sa.Column("priceUsd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("isActive", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("displayOrder", sa.Integer(), nullable=False, unique=True),
        sa.Column("createdAt", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("updatedAt", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('"credits" > 0'), sa.CheckConstraint('"priceInr" >= 0'), sa.CheckConstraint('"priceUsd" >= 0'),
    )
    op.add_column("PaymentOrder", sa.Column("topUpPackageId", sa.String(), nullable=True))
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key("PaymentOrder_topUpPackageId_fkey", "PaymentOrder", "TopUpPackage", ["topUpPackageId"], ["id"], ondelete="SET NULL")
    op.create_table(
        "CommercialConfigAudit",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("adminUserId", sa.String(), sa.ForeignKey("User.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("entityType", sa.String(), nullable=False), sa.Column("entityId", sa.String(), nullable=False), sa.Column("action", sa.String(), nullable=False),
        sa.Column("before", sa.JSON(), nullable=True), sa.Column("after", sa.JSON(), nullable=True), sa.Column("createdAt", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    plans = sa.table("PlanCommercialConfig", sa.column("id", sa.String()), sa.column("planKey", sa.String()), sa.column("name", sa.String()), sa.column("monthlyPriceInr", sa.Float()), sa.column("monthlyPriceUsd", sa.Float()), sa.column("projectLimit", sa.Integer()), sa.column("keywordLimit", sa.Integer()), sa.column("monthlyCredits", sa.Integer()), sa.column("automaticCredits", sa.Integer()), sa.column("manualRefreshLimit", sa.Integer()), sa.column("keywordResearchLimit", sa.Integer()), sa.column("competitorSpyLimit", sa.Integer()))
    op.bulk_insert(plans, [
        {"id": "commercial-free", "planKey": "free_trial", "name": "Free", "monthlyPriceInr": 0, "monthlyPriceUsd": 0, "projectLimit": 1, "keywordLimit": 5, "monthlyCredits": 100, "automaticCredits": 0, "manualRefreshLimit": 0, "keywordResearchLimit": 0, "competitorSpyLimit": 0},
        {"id": "commercial-starter", "planKey": "starter", "name": "Starter", "monthlyPriceInr": 999, "monthlyPriceUsd": 14, "projectLimit": 1, "keywordLimit": 100, "monthlyCredits": 8000, "automaticCredits": 5000, "manualRefreshLimit": 10, "keywordResearchLimit": 10, "competitorSpyLimit": 3},
        {"id": "commercial-pro", "planKey": "pro", "name": "Pro", "monthlyPriceInr": 3999, "monthlyPriceUsd": 52, "projectLimit": 5, "keywordLimit": 500, "monthlyCredits": 40000, "automaticCredits": 25000, "manualRefreshLimit": 50, "keywordResearchLimit": 30, "competitorSpyLimit": 10},
        {"id": "commercial-agency", "planKey": "agency", "name": "Agency", "monthlyPriceInr": 9999, "monthlyPriceUsd": 130, "projectLimit": 20, "keywordLimit": 1500, "monthlyCredits": 120000, "automaticCredits": 75000, "manualRefreshLimit": 150, "keywordResearchLimit": 75, "competitorSpyLimit": 25},
    ])
    packages = sa.table("TopUpPackage", sa.column("id", sa.String()), sa.column("name", sa.String()), sa.column("credits", sa.Integer()), sa.column("priceInr", sa.Float()), sa.column("priceUsd", sa.Float()), sa.column("displayOrder", sa.Integer()))
    op.bulk_insert(packages, [{"id": f"topup-{m}", "name": f"{m * 600:,} credits", "credits": m * 600, "priceInr": m * 100, "priceUsd": 0, "displayOrder": i} for i, m in enumerate((1, 2, 3, 5, 10), 1)])


def downgrade():
    op.drop_table("CommercialConfigAudit")
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("PaymentOrder_topUpPackageId_fkey", "PaymentOrder", type_="foreignkey")
    op.drop_column("PaymentOrder", "topUpPackageId")
    op.drop_table("TopUpPackage")
    op.drop_table("PlanCommercialConfig")
    op.drop_column("User", "isAdmin")
