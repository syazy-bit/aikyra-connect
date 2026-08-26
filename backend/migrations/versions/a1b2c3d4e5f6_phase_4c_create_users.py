"""phase 4c create users table

Introduces user accounts for platform authentication:

- `users` table: identity (email, full_name), authentication
  (hashed_password via bcrypt), account status flags (is_active,
  is_verified), and standard timestamps.
- Unique functional index on lower(email) for case-insensitive
  email uniqueness and login lookups.

Additive only — no changes to existing tables; fully backward
compatible with Phase 1–4B data.

Revision ID: a1b2c3d4e5f6
Revises: b7d4e9a1c3f6
Create Date: 2026-08-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'b7d4e9a1c3f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(length=254), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=250), nullable=True),
        sa.Column(
            'is_active', sa.Boolean(),
            server_default='true', nullable=False,
        ),
        sa.Column(
            'is_verified', sa.Boolean(),
            server_default='false', nullable=False,
        ),
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False,
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False,
        ),
    )
    op.create_index(
        'uq_users_email',
        'users',
        [sa.text('lower(email)')],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('uq_users_email', table_name='users')
    op.drop_table('users')
