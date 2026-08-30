"""phase 11: public photo evidence for reported problems

Adds an optional, single, public photo to a reported problem (challenge).
A challenge has at most one image stored on the local filesystem under
<uploads>/reports/<server-generated-id>.<ext>; the DB stores only the
server-generated relative reference in challenges.image_path.

image_path is nullable so existing challenges (reported without a photo)
remain valid with image_path = NULL. This migration only adds the column; it
never backfills data and never touches applications' filesystem storage.

Revision ID: s1t2u3v4w5x6
Revises: r6s7t8u9v0w1
Create Date: 2026-08-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 's1t2u3v4w5x6'
down_revision: Union[str, None] = 'r6s7t8u9v0w1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'challenges',
        sa.Column('image_path', sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('challenges', 'image_path')
