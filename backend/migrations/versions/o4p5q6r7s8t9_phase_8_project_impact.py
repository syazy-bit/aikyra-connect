"""phase 8 create project_impact_metrics table

Creates the generic project impact surface: free-form impact metrics
(name/value/unit/description) recorded against approved projects. Impact is
intentionally generic — different projects measure different outcomes, so
`value` stays a string ('120', '~85%', '4x') and nothing here hardcodes
metric types. Metrics cascade-delete with their project.

Revision ID: o4p5q6r7s8t9
Revises: n3o4p5q6r7s8
Create Date: 2026-08-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'o4p5q6r7s8t9'
down_revision: Union[str, None] = 'n3o4p5q6r7s8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'project_impact_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'project_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('projects.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('name', sa.String(length=300), nullable=False),
        sa.Column('value', sa.String(length=100), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
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
        'ix_project_impact_metrics_project',
        'project_impact_metrics',
        ['project_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_project_impact_metrics_project', table_name='project_impact_metrics')
    op.drop_table('project_impact_metrics')