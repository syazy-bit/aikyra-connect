"""add admin capabilities and challenge review audit

Adds platform-level capability flags to users for admin dashboard access.
Adds validated_by to problem_dna for human DNA validation tracking.
Creates challenge_review_audit table for accountability.

Revision ID: v1w2x3y4z5a6
Revises: u5v6w7x8y9z0
Create Date: 2026-09-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'v1w2x3y4z5a6'
down_revision: Union[str, None] = 'u5v6w7x8y9z0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Reference existing enum types (they already exist in the database)
challenge_status_enum = postgresql.ENUM(
    'submitted', 'under_review', 'validated', 'rejected',
    name='challenge_status', create_type=False
)
dna_validation_status_enum = postgresql.ENUM(
    'pending_validation', 'validated', 'needs_review',
    name='dna_validation_status', create_type=False
)


def upgrade() -> None:
    # Add capability columns to users table
    op.add_column(
        'users',
        sa.Column(
            'can_review_problems',
            sa.Boolean(),
            nullable=False,
            server_default='false',
        ),
    )
    op.add_column(
        'users',
        sa.Column(
            'can_review_institutions',
            sa.Boolean(),
            nullable=False,
            server_default='false',
        ),
    )

    # Add validated_by to problem_dna
    op.add_column(
        'problem_dna',
        sa.Column(
            'validated_by',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )

    # Create challenge_review_audit table using existing enum types
    op.create_table(
        'challenge_review_audit',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('challenge_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('challenges.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('previous_status', challenge_status_enum, nullable=True),
        sa.Column('new_status', challenge_status_enum, nullable=True),
        sa.Column('previous_dna_validation_status', dna_validation_status_enum, nullable=True),
        sa.Column('new_dna_validation_status', dna_validation_status_enum, nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_challenge_review_audit_challenge', 'challenge_review_audit', ['challenge_id'], unique=False)
    op.create_index('ix_challenge_review_audit_reviewer', 'challenge_review_audit', ['reviewer_id'], unique=False)


def downgrade() -> None:
    # Drop challenge_review_audit table
    op.drop_index('ix_challenge_review_audit_reviewer', table_name='challenge_review_audit')
    op.drop_index('ix_challenge_review_audit_challenge', table_name='challenge_review_audit')
    op.drop_table('challenge_review_audit')

    # Drop validated_by from problem_dna
    op.drop_column('problem_dna', 'validated_by')

    # Drop capability columns from users
    op.drop_column('users', 'can_review_institutions')
    op.drop_column('users', 'can_review_problems')