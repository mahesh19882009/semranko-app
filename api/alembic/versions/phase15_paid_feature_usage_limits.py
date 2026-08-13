"""Add billing-cycle paid feature usage tracking.

Revision ID: phase15_feature_usage
Revises: phase14_add_indexes
"""

from alembic import op
import sqlalchemy as sa

revision = "phase15_feature_usage"
down_revision = "phase14_add_missing_indexes"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "FeatureUsage",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("userId", sa.String(), nullable=False),
        sa.Column("feature", sa.String(), nullable=False),
        sa.Column("cycleStart", sa.DateTime(), nullable=False),
        sa.Column("cycleEnd", sa.DateTime(), nullable=False),
        sa.Column("usedUnits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reservedUnits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("createdAt", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updatedAt", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('"usedUnits" >= 0', name="feature_usage_used_non_negative"),
        sa.CheckConstraint('"reservedUnits" >= 0', name="feature_usage_reserved_non_negative"),
        sa.ForeignKeyConstraint(["userId"], ["User.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("FeatureUsage_user_feature_cycle_key", "FeatureUsage", ["userId", "feature", "cycleStart"], unique=True)
    op.create_table(
        "FeatureUsageReservation",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("usageId", sa.String(), nullable=False),
        sa.Column("reference", sa.String(), nullable=False),
        sa.Column("units", sa.Integer(), nullable=False),
        sa.Column("consumedUnits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("createdAt", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updatedAt", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("units > 0", name="feature_usage_reservation_units_positive"),
        sa.CheckConstraint('"consumedUnits" >= 0', name="feature_usage_reservation_consumed_non_negative"),
        sa.ForeignKeyConstraint(["usageId"], ["FeatureUsage.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference"),
    )
    op.create_index("FeatureUsageReservation_usageId_idx", "FeatureUsageReservation", ["usageId"])


def downgrade():
    op.drop_index("FeatureUsageReservation_usageId_idx", table_name="FeatureUsageReservation")
    op.drop_table("FeatureUsageReservation")
    op.drop_index("FeatureUsage_user_feature_cycle_key", table_name="FeatureUsage")
    op.drop_table("FeatureUsage")
