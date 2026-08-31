"""rename institution membership role owner to institution_admin

Renames the 'owner' value of the institution_membership_role PostgreSQL enum to
'institution_admin'. The 'owner' role is an institution-membership role (a user
who manages an institution), not a platform user role; the clearer name is
'institution_admin'. representative, faculty and student are unchanged.

Uses the safe type-replacement strategy (same as j2k3l4m5n6o7):
1. Create a new enum type with the desired values
2. Alter the column to the new type with a USING clause that maps owner -> institution_admin
3. Drop the old enum type
4. Rename the new enum to the original name

Revision ID: u5v6w7x8y9z0
Revises: t6u7v8w9x0y1
Create Date: 2026-08-31

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'u5v6w7x8y9z0'
down_revision: Union[str, None] = 't6u7v8w9x0y1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Create the replacement enum with 'institution_admin' instead of 'owner'.
    op.execute(
        "CREATE TYPE institution_membership_role_new AS ENUM "
        "('institution_admin', 'representative', 'faculty', 'student')"
    )
    # Step 2: Alter the column to use the new enum type, mapping 'owner' -> 'institution_admin'
    # The USING clause maps the text representation of the old enum to the new enum,
    # converting 'owner' to 'institution_admin' while preserving other values.
    op.execute(
        "ALTER TABLE institution_memberships ALTER COLUMN role "
        "TYPE institution_membership_role_new "
        "USING CASE "
        "  WHEN role::text = 'owner' THEN 'institution_admin'::text "
        "  ELSE role::text "
        "END::institution_membership_role_new"
    )
    # Step 3: Drop the old enum type.
    op.execute("DROP TYPE institution_membership_role")
    # Step 4: Rename the replacement to the original name.
    op.execute(
        "ALTER TYPE institution_membership_role_new "
        "RENAME TO institution_membership_role"
    )


def downgrade() -> None:
    # Revert: create the enum with 'owner' but without 'institution_admin'.
    op.execute(
        "CREATE TYPE institution_membership_role_old AS ENUM "
        "('owner', 'representative', 'faculty', 'student')"
    )
    # Convert any institution_admin rows back to owner before downgrading.
    # Use USING clause to map institution_admin -> owner
    op.execute(
        "ALTER TABLE institution_memberships ALTER COLUMN role "
        "TYPE institution_membership_role_old "
        "USING CASE "
        "  WHEN role::text = 'institution_admin' THEN 'owner'::text "
        "  ELSE role::text "
        "END::institution_membership_role_old"
    )
    op.execute("DROP TYPE institution_membership_role")
    op.execute(
        "ALTER TYPE institution_membership_role_old "
        "RENAME TO institution_membership_role"
    )