"""phase 4c add pending_review to verification status

Adds the pending_review value to the institution_verification_status
enum using a safe type-replacement strategy:

1. Create a replacement enum containing all existing values + pending_review.
2. Migrate the column to use the replacement type.
3. Drop the old enum type.
4. Rename the replacement type to the original name.

This approach works within PostgreSQL transaction-level enum
limitations and preserves all existing data.

Revision ID: f3b9c2d1a8e7
Revises: e7a2b8f1c3d4
Create Date: 2026-08-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f3b9c2d1a8e7'
down_revision: Union[str, None] = 'e7a2b8f1c3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Create replacement enum with all values including pending_review.
    op.execute(
        "CREATE TYPE institution_verification_status_new AS ENUM "
        "('unverified', 'pending_review', 'verified', 'rejected', 'suspended')"
    )
    # Step 2: Alter the column to use the new enum type.
    op.execute(
        "ALTER TABLE institutions ALTER COLUMN verification_status "
        "TYPE institution_verification_status_new "
        "USING verification_status::text::institution_verification_status_new"
    )
    # Step 3: Drop the old enum type.
    op.execute("DROP TYPE institution_verification_status")
    # Step 4: Rename the replacement to the original name.
    op.execute(
        "ALTER TYPE institution_verification_status_new "
        "RENAME TO institution_verification_status"
    )


def downgrade() -> None:
    # Revert: create enum without pending_review, migrate, drop, rename.
    op.execute(
        "CREATE TYPE institution_verification_status_old AS ENUM "
        "('unverified', 'verified', 'rejected', 'suspended')"
    )
    # Convert any pending_review rows back to unverified before downgrading.
    op.execute(
        "UPDATE institutions SET verification_status = 'unverified' "
        "WHERE verification_status = 'pending_review'"
    )
    op.execute(
        "ALTER TABLE institutions ALTER COLUMN verification_status "
        "TYPE institution_verification_status_old "
        "USING verification_status::text::institution_verification_status_old"
    )
    op.execute("DROP TYPE institution_verification_status")
    op.execute(
        "ALTER TYPE institution_verification_status_old "
        "RENAME TO institution_verification_status"
    )
