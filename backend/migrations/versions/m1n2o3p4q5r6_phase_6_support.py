"""phase 6 create projects, organizations and support_offers tables

Creates the minimal industry/NGO support surface: an approved solution is
materialized as a project when a proposal is accepted, an organization
registers with a single manager, and support offers attach to projects.

Revision ID: m1n2o3p4q5r6
Revises: 5f6g7h8i9j0k
Create Date: 2026-08-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'm1n2o3p4q5r6'
down_revision: Union[str, None] = '5f6g7h8i9j0k'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. project_status enum
    op.execute("CREATE TYPE project_status AS ENUM ('active')")

    # 2. projects table
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'proposal_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('proposals.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'team_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('teams.id', ondelete='CASCADE'),
            nullable=False,
        ),
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
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column(
            'status',
            postgresql.ENUM(
                'active',
                name='project_status',
                # project_status is created explicitly above via CREATE TYPE.
                # create_type=False prevents SQLAlchemy from emitting a second
                # CREATE TYPE while creating this table (DuplicateObject).
                create_type=False,
            ),
            server_default='active',
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
    op.create_index('ix_projects_institution', 'projects', ['institution_id'])
    op.create_index('ix_projects_challenge', 'projects', ['challenge_id'])
    op.create_index('ix_projects_status', 'projects', ['status'])
    op.create_unique_constraint(
        'uq_projects_proposal',
        'projects',
        ['proposal_id'],
    )

    # 3. organizations table
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=250), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('website', sa.String(length=500), nullable=True),
        sa.Column(
            'manager_user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='RESTRICT'),
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
    op.create_index('ix_organizations_manager', 'organizations', ['manager_user_id'])
    op.create_index(
        'uq_organizations_name_normalized',
        'organizations',
        [sa.text(
            "lower(btrim(regexp_replace(regexp_replace(name, '[^a-zA-Z0-9]+', ' ', 'g'), "
            "'\\s+', ' ', 'g')))"
        )],
        unique=True,
    )

    # 4. support_type and support_offer_status enums
    op.execute(
        "CREATE TYPE support_type AS ENUM "
        "('funding', 'equipment', 'mentorship', 'pilot_support')"
    )
    op.execute("CREATE TYPE support_offer_status AS ENUM ('offered')")

    # 5. support_offers table
    op.create_table(
        'support_offers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'project_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('projects.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'organization_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('organizations.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'offered_by',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='RESTRICT'),
            nullable=False,
        ),
        sa.Column(
            'support_type',
            postgresql.ENUM(
                'funding',
                'equipment',
                'mentorship',
                'pilot_support',
                name='support_type',
                # support_type is created explicitly above via CREATE TYPE.
                # create_type=False prevents SQLAlchemy from emitting a second
                # CREATE TYPE while creating this table (DuplicateObject).
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column(
            'status',
            postgresql.ENUM(
                'offered',
                name='support_offer_status',
                # support_offer_status is created explicitly above via CREATE
                # TYPE. create_type=False prevents SQLAlchemy from emitting a
                # second CREATE TYPE while creating this table
                # (DuplicateObject).
                create_type=False,
            ),
            server_default='offered',
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
    op.create_index('ix_support_offers_project', 'support_offers', ['project_id'])
    op.create_index('ix_support_offers_organization', 'support_offers', ['organization_id'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('ix_support_offers_organization', table_name='support_offers')
    op.drop_index('ix_support_offers_project', table_name='support_offers')
    op.drop_table('support_offers')

    op.execute("DROP TYPE support_offer_status")
    op.execute("DROP TYPE support_type")

    op.drop_index('uq_organizations_name_normalized', table_name='organizations')
    op.drop_index('ix_organizations_manager', table_name='organizations')
    op.drop_table('organizations')

    op.drop_constraint('uq_projects_proposal', 'projects', type_='unique')
    op.drop_index('ix_projects_status', table_name='projects')
    op.drop_index('ix_projects_challenge', table_name='projects')
    op.drop_index('ix_projects_institution', table_name='projects')
    op.drop_table('projects')

    op.execute("DROP TYPE project_status")
