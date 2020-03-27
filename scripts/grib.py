"""
Proof of concept for importing grib2 files into postgis.
NOTE: in order for this to run, one needs postgress installed on the local machine, as it uses raster2pgsql.

Notes to future self:
# 1'st, I tried eccodes, iterating through records.

eccodes is a bit of a pain, you need to compile it, and then you
can iterate through each of the records of the grib file. You'd have
to then populate a geospatial db to query - I didn't get that far.

It's worth looking at alternatives to eccodes, like gdal can also do it for
you.

I think this is going to be the route to go!

# 2nd, I tried importing rasters directly into postgis.

There are problems with this. It's real easy to get the data in, and to do a query,
but queries are slow when there are multiple rasters involved.

I tried cropping the data, to only BC, to see how much faster I could get it - see below:

Crop the raster to contain BC only:
INSERT INTO wps.temperature (rid, rast, filename)
SELECT nextval('temperature_rid_seq'), ST_Clip(rast,
			  ST_MakePolygon( 
	ST_GeomFromText('LINESTRING(-140 61,-113 61,-113 47, -140 47, -140 61)'))
			  , false),
			  filename from wps.temperature
			  where rid <= 243;

Now select using only the cropped records:
select rid, filename, ST_Value(rast, foo.pt_geom) as v1 from wps.temperature cross join 
(select ST_SetSRID(ST_Point(-123.38544, 48.44023), 0) as pt_geom) as foo
where rid > 243
order by filename

It was faster, on my computer, it went from 6 seconds, to 2 seconds - but that's
not fast enough! We need much faster results, since we need to pull a whole
bunch of values, not just temperature, so I don't think this is a good solution.


# Things to consider:
##  If going the grib -> sql -> postgis path:
- Making the raster smaller inside PostGIS, so it's only B.C. might speed things up.
## If using the grib -> iterate -> postgis path
- Using gdal to iterate through instead of eccodes.
"""
import subprocess
from datetime import datetime
import os

import psycopg2
import wget


def get_db_connection():
    """
    Get a DB connection, assuming you're running postgis running in docker.
    """
    return psycopg2.connect(host="127.0.0.1", dbname="wps", user="wps", password="wps")


def get_url(forecast_hour: str):
    """
    Get URL for the grib file.

    forecastHour : [000, 003, …, 192, 198, 204, ..., 237, 240]
    """
    url = 'http://dd.weather.gc.ca/model_gem_global/25km/grib2/lat_lon/{HH}/{hhh}/'.format(
        HH='00', hhh=forecast_hour)

    # http://dd.weather.gc.ca/model_gem_global/25km/grib2/lat_lon/HH/hhh/
    # http://dd.weather.gc.ca/model_gem_global/25km/grib2/lat_lon/00/000/

    # https://weather.gc.ca/grib/GLB_HR/GLB_latlonp24xp24_P000_deterministic_e.html
    # https://weather.gc.ca/grib/grib2_glb_25km_e.html#variables
    # 4	Temperature	2m above ground	TMP_TGL_2m	Kelvin
    variable = 'TMP'
    level_type = 'TGL'
    level = '2'

    # Projection: projection used for the data. Can take the values [latlon, ps]
    projection = 'latlon.24x.24'

    date = datetime.now().strftime('%Y%m%d00')

    # CMC_glb_Variable_LevelType_Level_projection_YYYYMMDDHH_Phhh.grib2
    filename = 'CMC_glb_{Variable}_{LevelType}_{Level}_{projection}_{YYYYMMDDHH}_P{hhh}.grib2'.format(
        Variable=variable, LevelType=level_type, Level=level, projection=projection, YYYYMMDDHH=date,
        hhh=forecast_hour)

    return url, filename


def download_grib_files(folder: str):
    """
    Download grib files

    # https://weather.gc.ca/grib/grib2_glb_25km_e.html
    # https://weather.gc.ca/grib/usage_tips_e.html

    https://weather.gc.ca/grib/grib2_ens_geps_e.html:

    The data can be accessed at the following URLs:
    http://dd.weather.gc.ca/ensemble/geps/grib2/raw/HH/hhh/

    where:

    raw: is a constant string indicating model data is raw (not processed)
    HH: model run start, in UTC [00,12]
    hhh: forecast hour [000, 003, …, 192, 198, 204, ..., 378, 384] and [000, 003, …, 192, 198, 204, ...,
            762, 768] each Thursday at 000UTC

    https://weather.gc.ca/grib/grib2_ens_geps_e.html::

    The file names have the following nomenclature:
    CMC_geps-raw_Variable_LevelType_Level_latlonResolution_YYYYMMDDHH_Phhh_allmbrs.grib2

    where:

    CMC_geps-raw: constant string indicating that the data is from the Canadian Meteorological Centre (CMC),
        the model used (geps: Global Ensemble Prediction System) and the data type (raw).
    Resolution: Constant string indicating the data resolution (0p5x0p5)
    Variable: Variable type included in this file. To consult a complete list, refer to the variables section.
    LevelType: Level type. To consult a complete list, refer to the variables section.
    Level: Level value. To consult a complete list, refer to the variables section.
    YYYYMMDD: Year, month and day of the beginning of the forecast.
    HH: UTC run time [00,12]
    Phhh: P is a constant character. hhh is the forecast hour [000, 003, …, 192, 198, 204, ..., 378, 384] or
        [000, 003, …, 192, 198, 204, ..., 762, 768] each Thursday at 000UTC
    allmbrs: constant string indicating that all the members of the ensemble are included in this file
    grib2: constant string indicating the GRIB2 format is used
    Example of file name:
    CMC_geps-raw_UGRD_ISBL_0925_latlon0p5x0p5_2010090100_P078_allmbrs.grib2

    This file originates from the Canadian Meteorological Center (CMC) and contains the raw data of the
        Global Ensemble Prediction System (CMC_geps-raw). The data in the file start on September 1st 2010 at
        00Z (2010090100). It contains the U-component wind (UGRD) at the isobaric level 925 mb (ISBL_0925)
        for the forecast hour 78 (P078), for all members (allmbrs) in GRIB2 format (.grib2).
    """
    if not os.path.exists(folder):
        os.makedirs(folder)
    # The prediction runs for 10 days. 10 days x 24 hours
    for forecast_hour in ['{:03d}'.format(hour) for hour in range(0, 10*24+1, 3)]:
        url, filename = get_url(forecast_hour=forecast_hour)
        grib_url = '{}{}'.format(url, filename)
        if os.path.exists(os.path.join(folder, filename)):
            print('skip {}'.format(grib_url))
        else:
            print('downloading {}'.format(grib_url))
            wget.download(grib_url, out=folder)


def generate_sql(folder: str):
    """
    Now iterate through the grib files, creating sql files.
    """
    for filename in os.listdir(folder):
        if filename.endswith('.grib2'):
            if os.path.exists(os.path.join(folder, '{}.sql'.format(filename))):
                print('skipping {} since sql for it already exists'.format(filename))
            else:
                outfile_name = os.path.join(folder, '{}.sql'.format(filename))
                with open(outfile_name, 'w') as outfile:
                    # see: https://postgis.net/docs/using_raster_dataman.html
                    process = subprocess.Popen(
                        ['raster2pgsql',
                         '-F',  # Add a column with the name of the file.
                         '-a',  # Append raster(s) to an existing table.
                         '{folder}/{grib}'.format(folder=folder,
                                                  grib=filename),
                         'wps.temperature'],
                        stdout=outfile,
                        stderr=subprocess.PIPE)
                    stdout, stderr = process.communicate()  # pylint: disable=unused-variable
                    print(stderr)


def run_sql_script(file: str):
    """
    Execute some sql script.
    """
    print('execute {}'.format(file))
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            with open(file, 'r') as infile:
                cursor.execute(infile.read())


def prepare_database():
    """
    Create tables and things in the database.
    """
    try:
        run_sql_script('scripts/create_temperature.sql')
    except psycopg2.errors.DuplicateTable as exception:  # pylint: disable=no-member
        print(exception)


def filename_in_db(filename: str):
    """
    Check if the filename doesn't already exist.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                'select filename from wps.temperature where filename = %s', (filename, ))
            return cursor.fetchone() is not None


def import_sql(folder: str):
    """
    Import raster sql.
    """
    print('Importing raster data into PostGIS.')
    for filename in os.listdir(folder):
        if filename.endswith('.sql'):
            if filename_in_db(filename[:-4]):
                print('skipping {}, already imported'.format(filename))
            else:
                run_sql_script(os.path.join(folder, filename))


def print_prediction(lon, lat):
    """
    Print the predicted temperature for a given point.
    """
    print('printing preduction for {} {}'.format(lon, lat))
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """select rid, filename, ST_Value(rast, foo.pt_geom) as v1
                from wps.temperature
                cross join (select ST_SetSRID(ST_Point({}, {}), 0) as pt_geom) as foo
                order by filename""".format(lon, lat))
            for row in cursor.fetchall():
                print(row)


def main():
    """
    Main entry point.
    """
    working_directory = 'grib'
    # 1. Download grib files.
    download_grib_files(working_directory)
    # 2. Generate postgis sql files.
    generate_sql(working_directory)
    # 3. Prepare the database (make a table for it to go in).
    prepare_database()
    # 4. Import all the sql files into postgis.
    import_sql(working_directory)
    # 5. Now for the proof of concept!!!
    print_prediction(-123.38544, 48.44023)


if __name__ == "__main__":
    main()
