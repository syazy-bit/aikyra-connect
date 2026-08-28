"""phase 5 create teams and team_memberships tables

Adds faculty and student roles to institution_membership_role.
Creates teams and team_memberships tables with enums.

Revision ID: g4h5i6j7k8l9
Revises: f3b9c2d1a8e7
Create Date: 2026-08-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'g4h5i6j7k8l9'
down_revision: Union[str, None] = 'f3b9c2d1a8e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add faculty and student to institution_membership_role
    op.execute("ALTER TYPE institution_membership_role ADD VALUE 'faculty'")
    op.execute("ALTER TYPE institution_membership_role ADD VALUE 'student'")

    # 2. Create team_status enum
    op.execute(
        "CREATE TYPE team_status AS ENUM "
        "('forming', 'active', 'submitted', 'archived')"
    )

    # 3. Create team_role enum
    op.execute(
        "CREATE TYPE team_role AS ENUM "
        "('lead', 'member')"
    )

    # 4. Create team_membership_status enum
    op.execute(
        "CREATE TYPE team_membership_status AS ENUM "
        "('active', 'invited', 'removed')"
    )

    # 5. Create teams table
    op.create_table(
        'teams',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'institution_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('institutions.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'challenge_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('challenges.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column(
            'status',
            sa.String(length=20),
            nullable=False,
            server_default='forming',
        ),
        sa.Column(
            'created_by',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id'),
            nullable=False,
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )
    op.create_index('ix_teams_institution', 'teams', ['institution_id'])
    op.create_index('ix_teams_challenge', 'teams', ['challenge_id'])
    op.create_index('ix_teams_created_by', 'teams', ['created_by'])
    op.create_unique_constraint(
        'uq_team_inst_challenge_name',
        'teams',
        ['institution_id', 'challenge_id', 'name'],
    )

    # 6. Create team_memberships table
    op.create_table(
        'team_memberships',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'team_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('teams.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'role',
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            'status',
            sa.String(length=20),
            nullable=False,
            server_default='active',
        ),
        sa.Column(
            'invited_by',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id'),
            nullable=True,
        ),
        sa.Column(
            'joined_at',
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )
    op.create_index('ix_team_memberships_team', 'team_memberships', ['team_id'])
    op.create_index('ix_team_memberships_user', 'team_memberships', ['user_id'])
    op.create_index('ix_team_memberships_invited_by', 'team_memberships', ['invited_by'])
    op.create_unique_constraint(
        'uq_team_membership_user',
        'team_memberships',
        ['team_id', 'user_id'],
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_constraint('uq_team_membership_user', 'team_memberships', type_='unique')
    op.drop_index('ix_team_memberships_invited_by', table_name='team_memberships')
    op.drop_index('ix_team_memberships_user', table_name='team_memberships')
    op.drop_index('ix_team_memberships_team', table_name='team_memberships')
    op.drop_table('team_memberships')

    op.drop_constraint('uq_team_inst_challenge_name', 'teams', type_='unique')
    op.drop_index('ix_teams_created_by', table_name='teams')
    op.drop_index('ix_teams_challenge', table_name='teams')
    op.drop_index('ix_teams_institution', table_name='teams')
    op.drop_table('teams')

    # Drop enums in reverse order
    op.execute("DROP TYPE team_membership_status")
    op.execute("DROP TYPE team_role")
    op.execute("DROP TYPE team_status")

    # Remove faculty and student from institution_membership_role
    # PostgreSQL doesn't support DROP VALUE, so we use the safe replacement strategy
    #
    # NOTE: Any faculty/student rows are converted back to a valid role by the
    # later Platform Reviewer migration (j2k3l4m5n6o7) downgrade, which runs
    # before this one in the downgrade chain. Since that migration already
    # maps faculty/student -> representative, no additional row conversion is
    # needed here — and the literals 'student'/'faculty' would not be valid
    # values in the target enum.
    op.execute(
        "CREATE TYPE institution_membership_role_old AS ENUM "
        "('owner', 'representative', 'reviewer')"
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