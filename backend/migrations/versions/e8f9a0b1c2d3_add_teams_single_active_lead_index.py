"""enforce exactly one active team lead

Adds a partial unique index on team_memberships (team_id) restricted to
rows where role='lead' AND status='active', so each team can have at most
one active lead at the database level.

This backs the CP2 leadership-transfer invariant: demoting the current
lead before promoting the target never violates the index, and any
race that would create two active leads fails with an IntegrityError.

Revision ID: e8f9a0b1c2d3
Revises: a3b4c5d6e7f8
Create Date: 2026-08-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e8f9a0b1c2d3'
down_revision: Union[str, None] = 'a3b4c5d6e7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'uq_teams_single_active_lead',
        'team_memberships',
        ['team_id'],
        unique=True,
        postgresql_where=sa.text("role = 'lead' AND status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index('uq_teams_single_active_lead', table_name='team_memberships')