import sys
import os
import pathlib
SCRIPT_PATH   = pathlib.Path(__file__).resolve()
ROOT_PATH     = SCRIPT_PATH.parent.parent
LOG_PATH      = os.path.join(ROOT_PATH.absolute(), 'logs', 'backtest_log.txt')
DATA_PATH     = os.path.join(ROOT_PATH.absolute(), 'data', 'crypto', 'poloniex')
POLONIEX_PATH = os.path.join(ROOT_PATH.absolute(), 'src', 'exchanges', 'crypto')
sys.path.insert(0, POLONIEX_PATH)
from poloniex import Poloniex

import time
import json
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
pd.set_option('display.max_rows', 100)
pd.set_option('display.max_columns', 10)
# pd.set_option('display.width', 1000)
import numpy as np


####################################################### CONSTANTS #######################################################

QUERI_POLONIEX = False
COIN1 = 'USDT'
COIN2 = 'BTC'
PAIR = COIN1 + '_' + COIN2
TF = 0.001 # TF = trading fee
INCLUDE_TF = True  # flag if we want to include the TF in our calculations
MAX_LEVERAGE = 2.0

# DATA_FILENAME = 'price_data_one_coin-%s_%s-2hr_intervals-ONE_YEAR-03_01_2018_8am_to_05_30_2019_6am.csv' % (COIN2, COIN1)
# DATA_FILENAME = 'price_data_one_coin-%s_%s-5min_intervals-ONE_DAY-02-20-2020-12am_to_02-21-2020-12am.csv' % (COIN2, COIN1)
# DATA_FILENAME = 'price_data_one_coin-%s_%s-5min_intervals-ONE_MONTH-01-21-2020-12am_to_02-21-2020-12am.csv' % (COIN2, COIN1)
DATA_FILENAME = 'price_data_one_coin-%s_%s-5min_intervals-ONE_QUARTER-11-21-2019-12am_to_02-21-2020-12am.csv' % (COIN2, COIN1)
BACKTEST_DATA_FILE = os.path.join(DATA_PATH, DATA_FILENAME)

#########################################################################################################################


# connect to Poloniex Exchange server
def poloniex_server():
    
    account = 'account1'

    data       = json.load(open('./api_keys.json', 'r'))
    api_key    = data['exchanges']['poloniex'][account]['api_key']
    secret_key = data['exchanges']['poloniex'][account]['secret_key']

    return Poloniex(api_key, secret_key)

# get backtesting data
def get_past_prices_from_poloniex(
    start_time_dt,
    end_time_dt,
    period,
    num_periods,
    save_to_csv=False,
    verbose=False):

    # get history data from startTime to endTime
    start_time_unix = time.mktime(start_time_dt.timetuple())
    end_time_unix   = time.mktime(end_time_dt.timetuple())

    conn = self.poloniex_server()

    # get history data of this currency into the dictionary
    prices = conn.api_query("returnChartData", {
            'currencyPair': PAIR,
            'start': start_time_unix,
            'end': end_time_unix,
            'period': period
        })

    prices2 = []
    for t in range(num_periods):  # remove unneeded data
        price = prices[t]['close']
        prices2.append({'unix_date': prices[t]['date'], COIN2: price})

    # create 'unix_date' and 'datetime' columns
    df = pd.DataFrame(prices2)
    df['datetime'] = df['unix_date'].apply(
        lambda unix_timestamp : \
        datetime.fromtimestamp(unix_timestamp))

    # reorder columns
    df = df[['unix_date', 'datetime', COIN2]]

    if save_to_csv:

        # USE THIS AS A TEMPLATE TO CREATE new_data_filename (replace "APPROX_DURATION" with the approximate duration of the backtest)
        new_data_filename = 'price_data_one_coin-%s_%s-5min_intervals-APPROX_DURATION-%S_to_%s.csv' % (
            COIN2, COIN1,
            start_time_dt.strftime('%Y-%m-%d-%I%p'),
            end_time_dt.strftime('%Y-%m-%d-%I%p'))
        new_backtest_data_file = os.path.join(DATA_PATH, new_data_filename)
        df.to_csv(new_backtest_data_file)

    if verbose: print('Successfully aquired price data from poloniex API.')
    return df
def get_past_prices_from_csv_file(verbose=False):
    if verbose: print('Successfully aquired price data from CSV file.')
    return pd.read_csv(BACKTEST_DATA_FILE, index_col=[0])

def setup_backtest(
    start_time_dt=datetime(2019, 11, 21, 0, 0, 0),  # year, month, day, hour, minute, second
    end_time_dt=datetime(  2020,  2, 21, 0, 0, 0),
    period= 5 * 60, # 5 min intervals between timesteps
    verbose=True):

    if verbose: print('\nInitializing Backtest ...')

    # period = duration of time between time steps (in seconds)
    # valid values:
    #   300 s   900 s    1800 s   7200 s   14400 s   86400 s
    #   5 min   15 min   30 min   2 hrs    4 hrs     1 day
    period_labels = {
        300   : '5 min',
        900   : '15 min',
        1800  : '30 min',
        7200  : '2 hrs',
        14400 : '4 hrs',
        86400 : '1 day'
    }

    # determine the proper number of time steps from start_time_dt to end_time_dt for the given period
    num_periods = int((end_time_dt - start_time_dt).total_seconds() / period)

    if verbose:
        print('Start Time ......................... %s' % start_time_dt.strftime('%Y-%m-%d-%I%p'))
        print('End Time ........................... %s' % end_time_dt.strftime('%Y-%m-%d-%I%p'))
        print('Time Step Duration ................. %s' % period_labels[period])
        print('Total Number of Time Steps ......... %d' % num_periods)

    # import backtest price data of COIN1 and COIN2 pair
    df = get_past_prices_from_poloniex(
            start_time_dt,
            end_time_dt,
            period,
            num_periods,
            verbose=verbose) \
        if QUERI_POLONIEX else \
        get_past_prices_from_csv_file(verbose=verbose)

    # get percent change of price each time step
    # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.pct_change.html
    df['pct_chg'] = df[COIN2].pct_change()
    df.drop([0], inplace=True) # remove first row (b/c it has a NaN value)
    df.reset_index(drop=True, inplace=True) # reset index accordingly
    # print(df)
    # input()
    # plt.plot(df[COIN2])
    # plt.title('%s Price Chart' % PAIR)
    # plt.ylabel('Price')
    # plt.xlabel('Time')
    # plt.show()

    if verbose: print('Backtest Initialized.\n')

    return df


if __name__ == '__main__':

    start_time_dt = datetime(2019, 11, 21, 0, 0, 0)
    end_time_dt = datetime(  2020,  2, 21, 0, 0, 0)
    period = 5 * 60 # 5 minute intervals
    df = setup_backtest(
        start_time_dt,
        end_time_dt,
        period,
        verbose=True)

    print(df)

    for t, row in df.iterrows():
        print('t = %d of %d\tunix_date = %s\tdatetime = %s\t%s price = %s\tpercent_change = %.2f %%' % (
            t, df.shape[0], row['unix_date'], row['datetime'], COIN2, row[COIN2], 100 * row['pct_chg']))
        time.sleep(1)

