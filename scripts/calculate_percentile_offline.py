from datetime import date
import pandas as pd
import json
import os
import matplotlib.pyplot as plt

# --------- INPUT PARAMETERS -----------------
# fire season start and end dates (month and day in numeric format) for location
# May 1 - Aug 31 used for now as MVP
FIRE_SEASON_START_MONTH = 5
FIRE_SEASON_START_DATE = 1
FIRE_SEASON_END_MONTH = 8
FIRE_SEASON_END_DATE = 31

# time range start and end years
# start of 1970 fire season to end of 2019 fire season is 50 years
# start of 2000 fire season to end of 2019 fire season is 20 years
# start of 2010 fire season to end of 2019 fire season is 10 years
RANGES = ((1970, 2019), (2000, 2019), (2010, 2019))
# RANGES = ((1970, 2019), )

# percentile to report out (in decimal format)
PERCENTILE = 0.9
# ------------ end of input parameters ---------

# ---------- GLOBAL VARIABLES ----------------
# import the CSV into Pandas dataframe
print('open file...')
daily_weather_data = pd.read_csv('../DailyWeather.csv')
# initialize empty Pandas Series for storing results
ffmc_percentiles, bui_percentiles, isi_percentiles, data_years = pd.Series(
    [], dtype=float), pd.Series([], dtype=float), pd.Series([], dtype=float), pd.Series([], dtype=object)
# create global Season instance to be used in output
season = {
    'start_month': FIRE_SEASON_START_MONTH,
    'start_day': FIRE_SEASON_START_DATE,
    'end_month': FIRE_SEASON_END_MONTH,
    'end_day': FIRE_SEASON_END_DATE
}
# ----------- end of global variables -------------


# the algorithm
def main():
    for item in RANGES:
        stations_json_to_dict()
        parse_weather_dates()
        remove_data_outside_date_range(item)
        remove_data_outside_fire_season()
        calculate_percentile_per_station()
        list_years_per_station()
        write_output_to_json(item)


def stations_json_to_dict():
    with open('../data/weather_stations.json') as fileHandle:
        global weather_stations
        weather_stations = json.load(fileHandle)['weather_stations']


def parse_weather_dates():
    print('parse_weather_dates...')
    # parse weather_date string into 3 columns: yyyy - mm - dd
    daily_weather_data['weather_date'] = daily_weather_data['weather_date'].apply(
        str)
    daily_weather_data['year'] = daily_weather_data['weather_date'].apply(
        lambda x: int(x[:4]))
    daily_weather_data['month'] = daily_weather_data['weather_date'].apply(
        lambda x: int(x[4:6]))
    daily_weather_data['day'] = daily_weather_data['weather_date'].apply(
        lambda x: int(x[6:]))

    daily_weather_data['date'] = daily_weather_data['weather_date'].apply(
        lambda x: date(int(x[:4]), int(x[4:6]), int(x[6:])))


def remove_data_outside_date_range(date_range):
    print('remove_data_outside_date_range... {}'.format(date_range))
    # remove data recorded before START_YEAR or after END_YEAR
    indexNames = daily_weather_data[(daily_weather_data['year']
                                     < date_range[0]) | (daily_weather_data['year'] > date_range[1])].index
    daily_weather_data.drop(indexNames, inplace=True)
    return


def remove_data_outside_fire_season():
    print('remove_data_outside_fire_season...')
    # remove data recorded outside of fire season
    indexNames = daily_weather_data[(daily_weather_data['month']
                                     < FIRE_SEASON_START_MONTH) | (daily_weather_data['month'] > FIRE_SEASON_END_MONTH)].index
    daily_weather_data.drop(indexNames, inplace=True)
    indexNames = daily_weather_data[(daily_weather_data['month'] == FIRE_SEASON_START_MONTH) & (
        daily_weather_data['day'] < FIRE_SEASON_START_DATE)].index
    daily_weather_data.drop(indexNames, inplace=True)
    indexNames = daily_weather_data[(daily_weather_data['month'] == FIRE_SEASON_END_MONTH) & (
        daily_weather_data['day'] > FIRE_SEASON_END_DATE)].index
    daily_weather_data.drop(indexNames, inplace=True)
    return


def calculate_percentile_per_station():
    print('calculate_percentile_per_station...')
    global ffmc_percentiles, bui_percentiles, isi_percentiles
    ffmc_percentiles = daily_weather_data.groupby(
        'station_code').ffmc.quantile(PERCENTILE)
    bui_percentiles = daily_weather_data.groupby(
        'station_code').bui.quantile(PERCENTILE)
    isi_percentiles = daily_weather_data.groupby(
        'station_code').isi.quantile(PERCENTILE)
    return


def list_years_per_station():
    print('list_years_per_station...')
    # data_years will be a pandas dataframe, which you can kind of think of as a
    # dictionary containing a list of integers.
    global data_years
    data_years = daily_weather_data.groupby('station_code').year.unique()
    data_years.apply(lambda x: x.sort())


def make_graph(station_summary, output_folder, date_range):
    global daily_weather_data
    station_code = station_summary['station']['code']
    indices = (
        {'key': 'ffmc', 'description': 'Fine Fuel Moisture Code'},
        {'key': 'bui', 'description': 'Buildup Index'},
        {'key': 'isi', 'description': 'Initial Spread Index'})

    # Get the bounding ranges for our x-axis (min and max date)
    min_date = date(date_range[0], 1, 1)
    max_date = date(date_range[1], 12, 31)
    # Filter for this station
    df = daily_weather_data.loc[daily_weather_data['station_code'] == int(
        station_code)]

    print('Generate images for - {} {}'.format(date_range, station_code))

    for index in indices:
        try:
            # Drop any rows without values
            index_df = df.dropna(subset=[index['key']])
            quantile = station_summary[index['key'].upper()]
            fig = plt.figure()
            ax1 = fig.add_subplot()
            ax1.set_xlabel('Date')
            ax1.set_ylabel('{} ({})'.format(
                index['description'], index['key'].upper()))
            title = "{} - {} ({}), Scatterplot".format(
                station_summary['station']['name'], index['description'], index['key'].upper())
            ax1.set_title(title)
            plt.hlines(quantile, xmin=min_date, xmax=max_date, colors='b',
                       linestyles='dashed', label='90th percentile : {}'.format(quantile))
            plt.scatter(index_df['date'], index_df[index['key']], 2)
            plt.legend()
            fig.savefig('{}/{}_{}.png'.format(output_folder,
                                              station_code, index['key']))
            plt.close()
        except AttributeError as e:
            print(e)


def write_output_to_json(date_range):
    print('write_output_to_json...')
    global weather_stations
    for weath_stat in weather_stations:
        key = weath_stat['code']
        if int(key) not in ffmc_percentiles:
            print('no ffmc percentile for {}'.format(key))
            continue

        ws = {'code': key, 'name': weath_stat['name']}
        try:
            station_summary = {
                'FFMC': ffmc_percentiles[int(key)],
                'ISI': isi_percentiles[int(key)],
                'BUI': bui_percentiles[int(key)],
                'season': season,
                'years': [int(year) for year in data_years[int(key)]],
                'station': ws
            }
            output_folder = "../data/{}-{}".format(
                date_range[0], date_range[1])
            if not os.path.exists(output_folder):
                os.mkdir(output_folder)
            output_filename = output_folder + "/" + key + ".json"
            with open(output_filename, 'w+') as json_file:
                json.dump(station_summary, json_file, indent=4)

            make_graph(station_summary, output_folder, date_range)

        except KeyError:
            print('Data not available for ' + key)

    return


if __name__ == '__main__':
    main()
