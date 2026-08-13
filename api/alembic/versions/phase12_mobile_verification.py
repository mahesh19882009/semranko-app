"""phase12_mobile_verification

Revision ID: phase12_mobile_verification
Revises: phase10_3_processing_job_recovery
Create Date: 2026-08-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'phase12_mobile_verification'
down_revision: Union[str, Sequence[str], None] = 'phase10_3_processing_job_recovery'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.engine import Engine
    engine: Engine = op.get_bind()
    inspector = sa_inspect(engine)

    user_columns = [c["name"] for c in inspector.get_columns("User")]
    
    if "mobileNumber" not in user_columns:
        op.add_column('User', sa.Column('mobileNumber', sa.String(), nullable=True, unique=True))
    
    if "mobileVerified" not in user_columns:
        op.add_column('User', sa.Column('mobileVerified', sa.Boolean(), nullable=False, server_default='false'))
    
    if "mobileVerificationOtp" not in user_columns:
        op.add_column('User', sa.Column('mobileVerificationOtp', sa.String(), nullable=True))
    
    if "mobileVerificationExpiresAt" not in user_columns:
        op.add_column('User', sa.Column('mobileVerificationExpiresAt', sa.DateTime(), nullable=True))
    
    if "mobileOtpAttempts" not in user_columns:
        op.add_column('User', sa.Column('mobileOtpAttempts', sa.Integer(), nullable=False, server_default='0'))
    
    if "mobileOtpLastSentAt" not in user_columns:
        op.add_column('User', sa.Column('mobileOtpLastSentAt', sa.DateTime(), nullable=True))

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("User")}
    if "User_mobileNumber_idx" not in existing_indexes:
        op.create_index('User_mobileNumber_idx', 'User', ['mobileNumber'])


def downgrade() -> None:
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.engine import Engine
    engine: Engine = op.get_bind()
    inspector = sa_inspect(engine)

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("User")}
    if "User_mobileNumber_idx" in existing_indexes:
        op.drop_index('User_mobileNumber_idx', table_name='User')

    user_columns = [c["name"] for c in inspector.get_columns("User")]
    
    if "mobileOtpLastSentAt" in user_columns:
        op.drop_column('User', 'mobileOtpLastSentAt')
    if "mobileOtpAttempts" in user_columns:
        op.drop_column('User', 'mobileOtpAttempts')
    if "mobileVerificationExpiresAt" in user_columns:
        op.drop_column('User', 'mobileVerificationExpiresAt')
    if "mobileVerificationOtp" in user_columns:
        op.drop_column('User', 'mobileVerificationOtp')
    if "mobileVerified" in user_columns:
        op.drop_column('User', 'mobileVerified')
    if "mobileNumber" in user_columns:
        op.drop_column('User', 'mobileNumber')
