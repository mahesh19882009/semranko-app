"""Persist the server-authoritative subscription billing period on orders.

Revision ID: phase18_payment_order_billing_cycle
Revises: phase17_permanent_free_defaults
"""

from alembic import op
import sqlalchemy as sa


revision = "phase18_payment_order_billing_cycle"
down_revision = "phase17_permanent_free_defaults"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "PaymentOrder",
        sa.Column("billingCycle", sa.String(), nullable=False, server_default="monthly"),
    )


def downgrade():
    op.drop_column("PaymentOrder", "billingCycle")
