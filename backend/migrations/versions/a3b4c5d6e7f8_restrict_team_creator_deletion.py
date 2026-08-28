"""restrict deletion of users who created teams

Make teams.created_by FK ON DELETE RESTRICT explicit.

Deleting a user who created teams must not cascade-delete those teams
(which would also cascade team memberships and break data integrity).
RESTRICT blocks the deletion until the referencing rows are removed.

Revision ID: a3b4c5d6e7f8
Revises: j2k3l4m5n6o7
Create Date: 2026-08-28

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, None] = 'j2k3l4m5n6o7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('teams_created_by_fkey', 'teams', type_='foreignkey')
    op.create_foreign_key(
        'teams_created_by_fkey',
        'teams',
        'users',
        ['created_by'],
        ['id'],
        ondelete='RESTRICT',
    )


def downgrade() -> None:
    op.drop_constraint('teams_created_by_fkey', 'teams', type_='foreignkey')
    op.create_foreign_key(
        'teams_created_by_fkey',
        'teams',
        'users',
        ['created_by'],
        ['id'],
    )
