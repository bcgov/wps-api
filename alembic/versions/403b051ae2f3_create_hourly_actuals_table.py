"""create_hourly_actuals_table

Revision ID: 403b051ae2f3
Revises: 8a4983fe2f75
Create Date: 2020-07-06 17:04:14.098256

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '403b051ae2f3'
down_revision = '8a4983fe2f75'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'hourly_station_actuals',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('station_id', sa.Integer),
        sa.Column('weather_datetime', sa.DateTime),
        sa.Column('temp_valid', sa.Boolean),
        sa.Column('temperature', sa.Float),
        sa.Column('dewpoint', sa.Float),
        sa.Column('rh_valid', sa.Boolean),
        sa.Column('relative_humidity', sa.Integer),
        sa.Column('wind_direction_valid', sa.Boolean),
        sa.Column('wind_direction', sa.Integer),
        sa.Column('wind_speed_valid', sa.Boolean),
        sa.Column('wind_speed', sa.Float),
        sa.Column('precip_valid', sa.Boolean),
        sa.Column('precipitation', sa.Float),
        sa.Column('ffmc', sa.Float),
        sa.Column('isi', sa.Float),
        sa.Column('fwi', sa.Float)
    )
    op.create_unique_constraint('unique_station_id_and_datetime', 'hourly_station_actuals', ['station_id', 'weather_datetime'])
    op.create_table_comment(
        'hourly_station_actuals',
        'Hourly actual weather data for each weather station. Data pulled from bcfireweatherp1.nrs.gov.bc.ca'
    )


def downgrade():
    op.drop_table_comment('hourly_station_actuals')
    op.drop_constraint('unique_station_id_and_datetime', 'hourly_station_actuals')
    op.drop_table('hourly_station_actuals')
