# pylint: disable=invalid-name, missing-function-docstring
"""create_noon_forecast_table

Revision ID: 950799ad6525
Revises: 8a4983fe2f75
Create Date: 2020-07-07 09:29:19.833161

"""
import datetime
import sqlalchemy as sa
import pytz
from alembic import op

# revision identifiers, used by Alembic.
revision = '950799ad6525'
down_revision = '8a4983fe2f75'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'noon_forecasts',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('weather_date', sa.Date),
        sa.Column('station_code', sa.Integer),
        sa.Column('temp_valid', sa.Boolean),
        sa.Column('temperature', sa.Integer),
        sa.Column('rh_valid', sa.Boolean),
        sa.Column('relative_humidity', sa.Integer),
        sa.Column('wdir_valid', sa.Boolean),
        sa.Column('wind_direction', sa.Integer),
        sa.Column('wspeed_valid', sa.Boolean),
        sa.Column('wind_speed', sa.Float),
        sa.Column('precip_valid', sa.Boolean),
        sa.Column('precipitation', sa.Float),
        sa.Column('gc', sa.Float),
        sa.Column('ffmc', sa.Float),
        sa.Column('dmc', sa.Float),
        sa.Column('dc', sa.Float),
        sa.Column('isi', sa.Float),
        sa.Column('bui', sa.Float),
        sa.Column('fwi', sa.Float),
        sa.Column('danger_rating', sa.Integer),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.current_timestamp())
    )
    op.create_table_comment(
        'noon_forecasts',
        'Daily noon-time forecasts for weather stations. Data pulled from BC Fire Weather Phase 1 API'
    )


def downgrade():
    op.drop_table_comment('noon_forecasts')
    op.drop_table('noon_forecasts')
