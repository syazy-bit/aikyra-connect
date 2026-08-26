"""phase 4a institution foundation

Introduces institutions as ecosystem participants:

- Enum types: institution_type, institution_status,
  institution_verification_status.
- `institutions` table: identity, location, contact, taxonomy-referenced
  capability data (domains + fixed-section capabilities JSONB), lifecycle
  status, verification/trust fields, and a generated full-text search
  vector (name + description + location).
- Indexes: normalized-name uniqueness (lower(btrim(name))), type/status/
  verification btrees, GIN on domains (jsonb_path_ops) and search_vector.

Additive only — no changes to challenges or problem_dna; fully backward
compatible with Phase 1–3 data.

Revision ID: b7d4e9a1c3f6
Revises: 8c41a2f0d9e7
Create Date: 2026-08-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b7d4e9a1c3f6'
down_revision: Union[str, None] = '8c41a2f0d9e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEARCH_VECTOR_EXPRESSION = (
    "to_tsvector('english', coalesce(name, '') || ' ' || "
    "coalesce(description, '') || ' ' || coalesce(location, ''))"
)


def upgrade() -> None:
    institution_type = sa.Enum(
        'university', 'college', 'research_institute', 'innovation_hub',
        name='institution_type',
    )
    institution_status = sa.Enum(
        'active', 'inactive',
        name='institution_status',
    )
    verification_status = sa.Enum(
        'unverified', 'verified', 'rejected', 'suspended',
        name='institution_verification_status',
    )

    op.create_table(
        'institutions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=250), nullable=False),
        sa.Column('institution_type', institution_type, nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('location', sa.String(length=200), nullable=False),
        sa.Column('website', sa.String(length=500), nullable=True),
        sa.Column('contact_email', sa.String(length=254), nullable=True),
        sa.Column('domains', postgresql.JSONB(), nullable=False),
        sa.Column('capabilities', postgresql.JSONB(), nullable=False),
        sa.Column(
            'status', institution_status,
            server_default='active', nullable=False,
        ),
        sa.Column(
            'verification_status', verification_status,
            server_default='unverified', nullable=False,
        ),
        sa.Column('verification_note', sa.Text(), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False,
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False,
        ),
        sa.Column(
            'search_vector',
            postgresql.TSVECTOR(),
            sa.Computed(SEARCH_VECTOR_EXPRESSION, persisted=True),
            nullable=True,
        ),
    )
    # Server-side defaults for NOT NULL JSONB columns (matches ORM defaults).
    op.execute("ALTER TABLE institutions ALTER COLUMN domains SET DEFAULT '[]'::jsonb")
    op.execute("ALTER TABLE institutions ALTER COLUMN capabilities SET DEFAULT '{}'::jsonb")

    op.create_index(
        'uq_institutions_name_normalized',
        'institutions',
        [
            sa.text(
                "lower(btrim(regexp_replace(regexp_replace(name, "
                "'[^a-zA-Z0-9]+', ' ', 'g'), '\\s+', ' ', 'g')))"
            )
        ],
        unique=True,
    )
    op.create_index('ix_institutions_type', 'institutions', ['institution_type'])
    op.create_index('ix_institutions_status', 'institutions', ['status'])
    op.create_index(
        'ix_institutions_verification_status',
        'institutions',
        ['verification_status'],
    )
    op.create_index(
        'ix_institutions_domains',
        'institutions',
        ['domains'],
        unique=False,
        postgresql_using='gin',
        postgresql_ops={'domains': 'jsonb_path_ops'},
    )
    op.create_index(
        'ix_institutions_search_vector',
        'institutions',
        ['search_vector'],
        unique=False,
        postgresql_using='gin',
    )


def downgrade() -> None:
    op.drop_index('ix_institutions_search_vector', table_name='institutions')
    op.drop_index('ix_institutions_domains', table_name='institutions')
    op.drop_index(
        'ix_institutions_verification_status', table_name='institutions'
    )
    op.drop_index('ix_institutions_status', table_name='institutions')
    op.drop_index('ix_institutions_type', table_name='institutions')
    op.drop_index('uq_institutions_name_normalized', table_name='institutions')
    op.drop_table('institutions')
    op.execute('DROP TYPE institution_verification_status')
    op.execute('DROP TYPE institution_status')
    op.execute('DROP TYPE institution_type')
