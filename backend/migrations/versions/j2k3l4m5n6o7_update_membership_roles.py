"""update institution membership roles for platform reviewer architecture

Removes 'reviewer' from institution_membership_role enum (now a platform-level privilege)
Adds 'faculty' and 'student' for Phase 5 institution-level roles

Uses safe type-replacement strategy:
1. Create new enum with desired values
2. Migrate column to new type
3. Drop old enum
4. Rename new enum to original name

Revision ID: j2k3l4m5n6o7
Revises: i1j2k3l4m5n6
Create Date: 2026-08-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'j2k3l4m5n6o7'
down_revision: Union[str, None] = 'i1j2k3l4m5n6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Create replacement enum with new values (no reviewer, add faculty, student)
    op.execute(
        "CREATE TYPE institution_membership_role_new AS ENUM "
        "('owner', 'representative', 'faculty', 'student')"
    )
    # Step 2: Migrate existing reviewer memberships to representative (safe fallback)
    # This preserves data integrity - existing reviewer memberships become representatives
    op.execute(
        "UPDATE institution_memberships SET role = 'representative' "
        "WHERE role = 'reviewer'"
    )
    # Step 3: Alter the column to use the new enum type
    op.execute(
        "ALTER TABLE institution_memberships ALTER COLUMN role "
        "TYPE institution_membership_role_new "
        "USING role::text::institution_membership_role_new"
    )
    # Step 4: Drop the old enum type
    op.execute("DROP TYPE institution_membership_role")
    # Step 5: Rename the replacement to the original name
    op.execute(
        "ALTER TYPE institution_membership_role_new "
        "RENAME TO institution_membership_role"
    )


def downgrade() -> None:
    # Revert: create enum with reviewer but without faculty, student
    op.execute(
        "CREATE TYPE institution_membership_role_old AS ENUM "
        "('owner', 'representative', 'reviewer')"
    )
    # Convert any faculty/student rows back to representative before downgrading
    op.execute(
        "UPDATE institution_memberships SET role = 'representative' "
        "WHERE role IN ('faculty', 'student')"
    )
    op.execute(
        "ALTER TABLE institution_memberships ALTER COLUMN role "
        "TYPE institution_membership_role_old "
        "USING role::text::institution_membership_role_old"
    )
    op.execute("DROP TYPE institution_membership_role")
    op.execute(
        "ALTER TYPE institution_membership_role_old "
        "RENAME TO institution_membership_role"
    )