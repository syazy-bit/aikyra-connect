"""phase 7 evolve project_status into the CP6 project lifecycle

The CP6 lifecycle reuses the existing projects.status column (its model
docstring always described it as the project lifecycle). The enum gains the
three lifecycle states and loses the single legacy 'active' value; existing
projects (all created by the accept -> project hook) are mapped to
'prototype', so no project data is lost and support offers keep working.

Revision ID: n3o4p5q6r7s8
Revises: m1n2o3p4q5r6
Create Date: 2026-08-29

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'n3o4p5q6r7s8'
down_revision: Union[str, None] = 'm1n2o3p4q5r6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_LABELS = "'prototype', 'pilot', 'implemented'"
OLD_LABEL = "'active'"


def upgrade() -> None:
    # The column default references the old enum member, so drop it before
    # recreating the type (PostgreSQL would otherwise fail to coerce it).
    op.execute("ALTER TABLE projects ALTER COLUMN status DROP DEFAULT")

    # Rename the existing type aside, recreate under the original name, then
    # cast the column values (always 'active' today) into the lifecycle enum.
    op.execute("ALTER TYPE project_status RENAME TO project_status_old")
    op.execute(f"CREATE TYPE project_status AS ENUM ({NEW_LABELS})")
    op.execute(
        "ALTER TABLE projects ALTER COLUMN status TYPE project_status "
        "USING (CASE status::text WHEN 'active' "
        "THEN 'prototype'::project_status "
        "ELSE status::text::project_status END)"
    )
    op.execute("ALTER TABLE projects ALTER COLUMN status SET DEFAULT 'prototype'")
    op.execute("DROP TYPE project_status_old")


def downgrade() -> None:
    op.execute("ALTER TABLE projects ALTER COLUMN status DROP DEFAULT")

    op.execute("ALTER TYPE project_status RENAME TO project_status_new")
    op.execute(f"CREATE TYPE project_status AS ENUM ({OLD_LABEL})")
    op.execute(
        "ALTER TABLE projects ALTER COLUMN status TYPE project_status "
        "USING 'active'::project_status"
    )
    op.execute("ALTER TABLE projects ALTER COLUMN status SET DEFAULT 'active'")
    op.execute("DROP TYPE project_status_new")