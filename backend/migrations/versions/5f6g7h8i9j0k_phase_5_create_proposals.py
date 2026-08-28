"""phase 5 create proposals table

Creates the proposals table and the proposal_status enum for solution
proposals (CP3 core). CP3 only makes draft/submitted/withdrawn reachable;
under_review/accepted/rejected are reserved for the CP4 review workflow.

Revision ID: 5f6g7h8i9j0k
Revises: e8f9a0b1c2d3
Create Date: 2026-08-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5f6g7h8i9j0k'
down_revision: Union[str, None] = 'e8f9a0b1c2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'proposals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'team_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('teams.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'challenge_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('challenges.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('approach', sa.Text(), nullable=True),
        sa.Column('resources_needed', sa.Text(), nullable=True),
        sa.Column('timeline', sa.Text(), nullable=True),
        sa.Column(
            'status',
            sa.Enum(
                'draft',
                'submitted',
                'under_review',
                'accepted',
                'rejected',
                'withdrawn',
                name='proposal_status',
            ),
            server_default='draft',
            nullable=False,
        ),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'reviewed_by',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id'),
            nullable=True,
        ),
        sa.Column('review_note', sa.Text(), nullable=True),
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
    op.create_index('ix_proposals_team_id', 'proposals', ['team_id'])
    op.create_index('ix_proposals_challenge_id', 'proposals', ['challenge_id'])
    op.create_index('ix_proposals_status', 'proposals', ['status'])
    op.create_unique_constraint(
        'uq_proposals_team_challenge',
        'proposals',
        ['team_id', 'challenge_id'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_proposals_team_challenge', 'proposals', type_='unique')
    op.drop_index('ix_proposals_status', table_name='proposals')
    op.drop_index('ix_proposals_challenge_id', table_name='proposals')
    op.drop_index('ix_proposals_team_id', table_name='proposals')
    op.drop_table('proposals')
    # drop_table does not remove the PostgreSQL enum type automatically.
    sa.Enum(
        'draft',
        'submitted',
        'under_review',
        'accepted',
        'rejected',
        'withdrawn',
        name='proposal_status',
    ).drop(op.get_bind(), checkfirst=True)