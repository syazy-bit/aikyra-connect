"""phase 3 discovery search foundation

Adds a generated full-text search vector on challenges (title + description
+ location, english config) with a GIN index, and a btree index on
problem_dna.primary_domain for domain-filtered discovery queries.

Additive only — fully backward compatible with Phase 1/2 data.

Revision ID: 8c41a2f0d9e7
Revises: 4140091755aa
Create Date: 2026-08-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8c41a2f0d9e7'
down_revision: Union[str, None] = '4140091755aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEARCH_VECTOR_EXPRESSION = (
    "to_tsvector('english', coalesce(title, '') || ' ' || "
    "coalesce(description, '') || ' ' || coalesce(location, ''))"
)


def upgrade() -> None:
    op.add_column(
        'challenges',
        sa.Column(
            'search_vector',
            postgresql.TSVECTOR(),
            sa.Computed(SEARCH_VECTOR_EXPRESSION, persisted=True),
            nullable=True,
        ),
    )
    op.create_index(
        'ix_challenges_search_vector',
        'challenges',
        ['search_vector'],
        unique=False,
        postgresql_using='gin',
    )
    op.create_index(
        'ix_problem_dna_primary_domain',
        'problem_dna',
        ['primary_domain'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_problem_dna_primary_domain', table_name='problem_dna')
    op.drop_index('ix_challenges_search_vector', table_name='challenges')
    op.drop_column('challenges', 'search_vector')
