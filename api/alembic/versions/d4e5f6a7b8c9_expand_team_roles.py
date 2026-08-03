"""Expand team roles to 4-role system

Revision ID: d4e5f6a7b8c9
Revises: 69bf9f4d7205
Create Date: 2026-08-02 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = '69bf9f4d7205'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Keep it simple: just add a check constraint instead of changing to enum type
    # This avoids the enum casting issues
    op.execute("""
        ALTER TABLE "TeamMember" 
        ADD CONSTRAINT check_team_role 
        CHECK (role IN ('Owner', 'Admin', 'Editor', 'Viewer'))
    """)
    
    # Update any existing invalid roles to Viewer
    op.execute("""
        UPDATE "TeamMember" 
        SET role = 'Viewer' 
        WHERE role NOT IN ('Owner', 'Admin', 'Editor', 'Viewer')
    """)


def downgrade() -> None:
    # Remove the check constraint
    op.execute("ALTER TABLE \"TeamMember\" DROP CONSTRAINT IF EXISTS check_team_role")
