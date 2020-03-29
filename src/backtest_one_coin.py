import sys
import os
import pathlib
SCRIPT_PATH = pathlib.Path(__file__).resolve()
ROOT_PATH   = SCRIPT_PATH.parent.parent
DATA_PATH   = os.path.join(ROOT_PATH.absolute(), 'data', 'crypto', 'poloniex')
# print(SCRIPT_PATH.absolute())
# print(ROOT_PATH.absolute())
# print(DATA_PATH)
# sys.exit()
POLONIEX_PATH = os.path.join(ROOT_PATH.absolute(), 'src', 'exchanges', 'crypto')
sys.path.insert(0, POLONIEX_PATH)
from poloniex import Poloniex

import time
import json
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
pd.set_option('display.max_rows', 10)
pd.set_option('display.max_columns', 10)
# pd.set_option('display.width', 1000)
import numpy as np

# constants
QUERI_POLONIEX = False
COIN1 = 'USDT'
COIN2 = 'BTC'
PAIR = COIN1 + '_' + COIN2
TRADING_FEE = 0.0025

DATA_FILENAME = 'price_data_one_coin-%s_%s-2hr_intervals-ONE_YEAR-03_01_2018_8am_to_05_30_2019_6am.csv' % (COIN2, COIN1)
DATA_FILENAME = 'price_data_one_coin-%s_%s-5min_intervals-ONE_DAY-02-20-2020-12am_to_02-21-2020-12am.csv' % (COIN2, COIN1)
DATA_FILENAME = 'price_data_one_coin-%s_%s-5min_intervals-ONE_MONTH-01-21-2020-12am_to_02-21-2020-12am.csv' % (COIN2, COIN1)
DATA_FILENAME = 'price_data_one_coin-%s_%s-5min_intervals-ONE_QUARTER-11-21-2019-12am_to_02-21-2020-12am.csv' % (COIN2, COIN1)
BACKTEST_DATA_FILE = os.path.join(DATA_PATH, DATA_FILENAME)


# pprint constants
DEBUG_WITH_CONSOLE = True
DEBUG_WITH_LOGFILE = True
DEBUG_LOGFILE_PATH = './log.txt'
DEFAULT_INDENT = '|  '
DEFAULT_DRAW_LINE = False


# pretty print the string
# arguments:
#   string = what will be printed
#   indent = what an indent looks like
#   num_indents = number of indents to put in front of the string
#   new_line_start = print a new line in before the string
#   new_line_end = print a new line in after the string
#   draw_line = draw a line on the blank line before or after the string
def pprint(string='',
    indent=DEFAULT_INDENT,
    num_indents=0,
    new_line_start=False,
    new_line_end=False,
    draw_line=DEFAULT_DRAW_LINE):

    if DEBUG_WITH_CONSOLE:

        total_indent0 = ''.join([indent] * num_indents)
        total_indent1 = ''.join([indent] * (num_indents + 1))

        if new_line_start:
            print(total_indent1 if draw_line else total_indent0)

        print(total_indent0 + string)

        if new_line_end:
            print(total_indent1 if draw_line else total_indent0)

    if DEBUG_WITH_LOGFILE:

        f = open(DEBUG_LOGFILE_PATH, 'a')

        new_indent = '\t'

        total_indent0 = ''.join([new_indent] * num_indents)
        total_indent1 = ''.join([new_indent] * (num_indents + 1))

        if new_line_start:
            f.write((total_indent1 if draw_line else total_indent0) + '\n')

        # all these regex's are to make tabs in the string properly
        # asdfasdf is to make sure there's no false positives
        # when replacing the indent
        indent2 = re.sub('\|', 'asdfasdf', indent)
        string = re.sub(indent2, new_indent, re.sub('\|', 'asdfasdf', string))
        f.write(total_indent0 + string + '\n')

        if new_line_end:
            f.write((total_indent1 if draw_line else total_indent0) + '\n')

        f.close()

# setup connection to servers
def poloniex_server():

    # select which account to use, options:
    # 'account1' aka lucius.dickerson@gmail.com
    # 'account2' aka private.mail285@gmail.com
    account = 'account1'

    data       = json.load(open('./api_keys.json', 'r'))
    api_key    = data['exchanges']['poloniex'][account]['api_key']
    secret_key = data['exchanges']['poloniex'][account]['secret_key']

    return Poloniex(api_key, secret_key)


# get backtesting data
def get_past_prices_from_poloniex(
    startTime, endTime, period, num_periods, conn):

    # get history data from startTime to endTime
    startTime_unix = time.mktime(startTime.timetuple())
    endTime_unix = time.mktime(endTime.timetuple())

    # get history data of this currency into the dictionary
    prices = conn.api_query("returnChartData", {
            'currencyPair': PAIR,
            'start': startTime_unix,
            'end': endTime_unix,
            'period': period
        })

    prices2 = []
    for t in num_periods:  # remove unneeded data
        price = prices[t]['close']
        prices2.append({'unix_date': prices[t]['date'], COIN2: price})

    # create 'unix_date' and 'datetime' columns
    df = pd.DataFrame(prices2)
    df['datetime'] = df['unix_date'].apply(
        lambda unix_timestamp : \
        datetime.fromtimestamp(unix_timestamp))

    # reorder columns
    df = df[['unix_date', 'datetime', COIN2]]

    df.to_csv(BACKTEST_DATA_FILE)

    return df

def get_past_prices_from_csv_file():

    return pd.read_csv(BACKTEST_DATA_FILE, index_col=[0])





if __name__ == '__main__':

    conn = poloniex_server()

    # variables
    startTime = datetime(2019, 11, 21, 0, 0, 0)  # year, month, day, hour, minute, second
    endTime   = datetime(2020,  2, 21, 0, 0, 0)
    # period = duration of time steps between rebalances
    #   300 s   900 s    1800 s   7200 s   14400 s   86400 s
    #   5 min   15 min   30 min   2 hrs    4 hrs     1 day
    period = 5 * 60  # duration of intervals between updates

    # determines the proper number of time steps from startTime to endTime for the given period
    num_periods = range(int((endTime - startTime).total_seconds() / period))

    # import backtest data of COIN1 and COIN2 pair
    df = get_past_prices_from_poloniex(startTime, endTime, period, num_periods, conn) \
        if QUERI_POLONIEX else get_past_prices_from_csv_file()

    # get percent change of price each time step
    # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.pct_change.html
    df['perc_chng'] = df[COIN2].pct_change()
    df.drop([0], inplace=True) # remove first row (b/c it has a NaN value)
    df.reset_index(drop=True, inplace=True) # reset index accordingly


    print(df)
    input()

    plt.plot(df[COIN2])
    plt.title('%s PriceChart' % PAIR)
    plt.ylabel('Price')
    plt.xlabel('Time')
    plt.show()

    for i, row in df.iterrows():
        date, price, perc_chng = row['datetime'], row[COIN2], row['perc_chng']
        print(i, date, price, perc_chng)

        input()
