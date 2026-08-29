"""phase 9 create project_reports table

Creates the outcome-report surface (CP8): one concise, lead-authored report
per implemented project (1:1 — project_id is UNIQUE) telling the conclusive
story of an approved solution: summary, results, lessons learned and next
steps. Like impact metrics, reports cascade-delete with their project; like
a project's title, they are project-scoped with no standalone public ID
route.

Revision ID: q5r6s7t8u9v0
Revises: o4p5q6r7s8t9
Create Date: 2026-08-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'q5r6s7t8u9v0'
down_revision: Union[str, None] = 'o4p5q6r7s8t9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'project_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'project_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('projects.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('results', sa.Text(), nullable=True),
        sa.Column('lessons_learned', sa.Text(), nullable=True),
        sa.Column('next_steps', sa.Text(), nullable=True),
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
        'uq_project_reports_project',
        'project_reports',
        ['project_id'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_project_reports_project', 'project_reports')
    op.drop_table('project_reports')