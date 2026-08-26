"""phase 4c create institution_memberships table

Introduces the institution_memberships join table linking users to
institutions with a role and status.

Enum types:
- institution_membership_role: owner, representative, reviewer
- institution_membership_status: active, invited, suspended

Constraints:
- uq_membership_user_institution: unique(user_id, institution_id)
- ix_membership_institution: index on institution_id
- ix_membership_user: index on user_id

Foreign keys:
- user_id -> users.id ON DELETE CASCADE
- institution_id -> institutions.id ON DELETE CASCADE

Additive only — no changes to existing tables; fully backward
compatible with Phase 1–4C data.

Revision ID: e7a2b8f1c3d4
Revises: a1b2c3d4e5f6
Create Date: 2026-08-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e7a2b8f1c3d4'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types explicitly so the column definitions can reference
    # them by name without SQLAlchemy attempting a second CREATE TYPE.
    op.execute("CREATE TYPE institution_membership_role AS ENUM "
               "('owner', 'representative', 'reviewer')")
    op.execute("CREATE TYPE institution_membership_status AS ENUM "
               "('active', 'invited', 'suspended')")

    op.create_table(
        'institution_memberships',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'user_id', postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'institution_id', postgresql.UUID(as_uuid=True),
            sa.ForeignKey('institutions.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'role', sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            'status', sa.String(length=20),
            server_default='active', nullable=False,
        ),
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False,
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False,
        ),
        sa.UniqueConstraint(
            'user_id', 'institution_id',
            name='uq_membership_user_institution',
        ),
    )
    op.create_index(
        'ix_membership_institution',
        'institution_memberships',
        ['institution_id'],
    )
    op.create_index(
        'ix_membership_user',
        'institution_memberships',
        ['user_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_membership_user', table_name='institution_memberships')
    op.drop_index('ix_membership_institution', table_name='institution_memberships')
    op.drop_table('institution_memberships')
    op.execute("DROP TYPE institution_membership_status")
    op.execute("DROP TYPE institution_membership_role")
