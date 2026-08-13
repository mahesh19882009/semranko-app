"""Separate spendable, purchased, and automatic tracking credit pools.

Revision ID: phase16_auto_credits
Revises: phase15_feature_usage
"""

from alembic import op
import sqlalchemy as sa


revision = "phase16_auto_credits"
down_revision = "phase15_feature_usage"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("User", sa.Column("planCreditBalance", sa.Float(), nullable=False, server_default="0"))
    op.add_column("User", sa.Column("purchasedCreditBalance", sa.Float(), nullable=False, server_default="0"))
    op.add_column("User", sa.Column("automaticCreditBalance", sa.Float(), nullable=False, server_default="0"))

    # Existing balances cannot be reliably divided between plan and top-up value.
    # Preserve all legacy value as purchased credits so migration cannot expire it.
    op.execute('UPDATE "User" SET "purchasedCreditBalance" = "creditBalance"')

    op.create_check_constraint("user_plan_credit_balance_non_negative", "User", '"planCreditBalance" >= 0')
    op.create_check_constraint("user_purchased_credit_balance_non_negative", "User", '"purchasedCreditBalance" >= 0')
    op.create_check_constraint("user_automatic_credit_balance_non_negative", "User", '"automaticCreditBalance" >= 0')

    op.add_column("CreditLedger", sa.Column("creditPool", sa.String(), nullable=False, server_default="spendable"))
    op.add_column("CreditLedger", sa.Column("planCreditsChange", sa.Float(), nullable=False, server_default="0"))
    op.add_column("CreditLedger", sa.Column("purchasedCreditsChange", sa.Float(), nullable=False, server_default="0"))
    op.add_column("CreditLedger", sa.Column("automaticCreditsChange", sa.Float(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("CreditLedger", "automaticCreditsChange")
    op.drop_column("CreditLedger", "purchasedCreditsChange")
    op.drop_column("CreditLedger", "planCreditsChange")
    op.drop_column("CreditLedger", "creditPool")
    op.drop_constraint("user_automatic_credit_balance_non_negative", "User", type_="check")
    op.drop_constraint("user_purchased_credit_balance_non_negative", "User", type_="check")
    op.drop_constraint("user_plan_credit_balance_non_negative", "User", type_="check")
    op.drop_column("User", "automaticCreditBalance")
    op.drop_column("User", "purchasedCreditBalance")
    op.drop_column("User", "planCreditBalance")
