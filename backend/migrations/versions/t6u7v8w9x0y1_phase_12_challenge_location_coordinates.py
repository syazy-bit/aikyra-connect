"""phase 12: optional precise coordinates for reported problems

Adds optional public latitude/longitude to a reported problem (challenge),
captured via the browser Geolocation API and shown as a "View on map" link.

Coordinates are stored at full 6-decimal precision (~0.1 m) as numeric(9,6).
Database-level CHECK constraints enforce the geographic ranges and that the
values form a pair (both NULL or both set), so partial coordinates can never
be persisted regardless of application logic.

latitude/longitude are nullable so existing challenges (reported without
coordinates) remain valid. This migration only adds columns + constraints; it
never backfills data.

Revision ID: t6u7v8w9x0y1
Revises: s1t2u3v4w5x6
Create Date: 2026-08-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 't6u7v8w9x0y1'
down_revision: Union[str, None] = 's1t2u3v4w5x6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'challenges',
        sa.Column('latitude', sa.Numeric(precision=9, scale=6), nullable=True),
    )
    op.add_column(
        'challenges',
        sa.Column('longitude', sa.Numeric(precision=9, scale=6), nullable=True),
    )
    op.create_check_constraint(
        'ck_challenges_latitude_range',
        'challenges',
        'latitude IS NULL OR (latitude >= -90 AND latitude <= 90)',
    )
    op.create_check_constraint(
        'ck_challenges_longitude_range',
        'challenges',
        'longitude IS NULL OR (longitude >= -180 AND longitude <= 180)',
    )
    op.create_check_constraint(
        'ck_challenges_coordinate_pair',
        'challenges',
        '(latitude IS NULL AND longitude IS NULL) '
        'OR (latitude IS NOT NULL AND longitude IS NOT NULL)',
    )


def downgrade() -> None:
    op.drop_constraint('ck_challenges_coordinate_pair', 'challenges', type_='check')
    op.drop_constraint('ck_challenges_longitude_range', 'challenges', type_='check')
    op.drop_constraint('ck_challenges_latitude_range', 'challenges', type_='check')
    op.drop_column('challenges', 'longitude')
    op.drop_column('challenges', 'latitude')
