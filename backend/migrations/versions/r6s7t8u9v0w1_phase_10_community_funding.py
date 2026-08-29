"""phase 10 community funding: verified funding goals and contributions

Adds the public "Approved Solution Community Funding" surface (AIKYRA VERIFIED
COMMUNITY FUNDING). A project (an approved solution) has at most one verified
funding goal (1:1 — project_id is UNIQUE, mirroring project_reports). Funding
progress is always aggregated server-side from COMPLETED contributions in
integer minor units (paise): PENDING/FAILED/REFUNDED money never counts, and
no per-supporter data is ever public.

Goals cascade-delete with their project; contributions cascade-delete with
their goal (the goal row, not the project, because a contribution is recorded
against a specific goal). The supporter account is a RESTRICT reference to
users — a contributor cannot be deleted while a contribution exists.

Revision ID: r6s7t8u9v0w1
Revises: q5r6s7t8u9v0
Create Date: 2026-08-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'r6s7t8u9v0w1'
down_revision: Union[str, None] = 'q5r6s7t8u9v0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. funding_goal_status and funding_contribution_status enums
    op.execute("CREATE TYPE funding_goal_status AS ENUM ('open', 'closed')")
    op.execute(
        "CREATE TYPE funding_contribution_status AS ENUM "
        "('pending', 'completed', 'failed', 'refunded')"
    )

    # 2. funding_goals table
    op.create_table(
        'funding_goals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'project_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('projects.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('goal_minor', sa.BigInteger(), nullable=False),
        sa.Column(
            'currency',
            sa.String(length=3),
            server_default='INR',
            nullable=False,
        ),
        sa.Column(
            'status',
            postgresql.ENUM(
                'open',
                'closed',
                name='funding_goal_status',
                # funding_goal_status is created explicitly above via CREATE
                # TYPE. create_type=False prevents SQLAlchemy from emitting a
                # second CREATE TYPE while creating this table
                # (DuplicateObject).
                create_type=False,
            ),
            server_default='open',
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
    op.create_unique_constraint(
        'uq_funding_goals_project',
        'funding_goals',
        ['project_id'],
    )
    op.create_index('ix_funding_goals_status', 'funding_goals', ['status'])
    op.create_check_constraint(
        'ck_funding_goals_goal_positive',
        'funding_goals',
        'goal_minor > 0',
    )
    op.create_check_constraint(
        'ck_funding_goals_currency_inr',
        'funding_goals',
        "currency = 'INR'",
    )

    # 3. funding_contributions table
    op.create_table(
        'funding_contributions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'goal_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('funding_goals.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'contributed_by',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='RESTRICT'),
            nullable=False,
        ),
        sa.Column('amount_minor', sa.BigInteger(), nullable=False),
        sa.Column(
            'status',
            postgresql.ENUM(
                'pending',
                'completed',
                'failed',
                'refunded',
                name='funding_contribution_status',
                # funding_contribution_status is created explicitly above via
                # CREATE TYPE. create_type=False prevents SQLAlchemy from
                # emitting a second CREATE TYPE while creating this table
                # (DuplicateObject).
                create_type=False,
            ),
            server_default='pending',
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
    op.create_index(
        'ix_funding_contributions_goal', 'funding_contributions', ['goal_id']
    )
    op.create_index(
        'ix_funding_contributions_status', 'funding_contributions', ['status']
    )
    op.create_check_constraint(
        'ck_funding_contributions_amount_positive',
        'funding_contributions',
        'amount_minor > 0',
    )


def downgrade() -> None:
    # Drop tables in reverse order.
    op.drop_index(
        'ix_funding_contributions_status', table_name='funding_contributions'
    )
    op.drop_index(
        'ix_funding_contributions_goal', table_name='funding_contributions'
    )
    op.drop_table('funding_contributions')

    op.drop_constraint(
        'ck_funding_goals_currency_inr', 'funding_goals', type_='check'
    )
    op.drop_constraint(
        'ck_funding_goals_goal_positive', 'funding_goals', type_='check'
    )
    op.drop_index('ix_funding_goals_status', table_name='funding_goals')
    op.drop_constraint(
        'uq_funding_goals_project', 'funding_goals', type_='unique'
    )
    op.drop_table('funding_goals')

    op.execute("DROP TYPE funding_contribution_status")
    op.execute("DROP TYPE funding_goal_status")