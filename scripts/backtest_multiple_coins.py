import time
import sys
sys.path.insert(0, './')
import json
from poloniex import poloniex
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
pd.set_option('display.max_rows', 10)
pd.set_option('display.max_columns', 10)
# pd.set_option('display.width', 1000)
import numpy as np



# constants
QUERI_POLONIEX = True
# BACKTEST_DATA_FILE = '../data/price_data_multiple_coins-BTC_ETH_XRP_LTC_ZEC_XMR_STR_DASH_ETC-2hr_intervals-08_01_2018_7am_to_08_01_2019_4am.csv'
BACKTEST_DATA_FILE = '../data/price_data_multiple_coins-BTC_ETH_XRP_LTC_ZEC_XMR_STR_DASH_ETC-5min_intervals_unknown_date_to_unknown_date.csv'
TETHER = 'USDT'
COINS = [
    'BTC',
    'ETH',
    'XRP',
    'LTC',
    'ZEC',
    'XMR',
    'STR',
    'DASH',
    'ETC',
]
PAIRS = [TETHER + '_' + coin for coin in COINS]
TRADING_FEE = 0.0025

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

    data = json.load(open('../../api_keys.json', 'r'))
    api_key = data[account]['api_key']
    secret_key = data[account]['secret_key']

    return poloniex(api_key, secret_key)

# get backtesting data
def get_past_prices_from_poloniex(
    startTime, endTime, period, num_periods, conn):

    # get history data from startTime to endTime
    startTime_unix = time.mktime(startTime.timetuple())
    endTime_unix = time.mktime(endTime.timetuple())

    # get price history data for each pair into a dictionary
    dct = { pair :
        conn.api_query("returnChartData", {
            'currencyPair': pair,
            'start': startTime_unix,
            'end': endTime_unix,
            'period': period
        }) for pair in PAIRS}

    # create 'unix_date' and 'datetime' columns
    df = pd.DataFrame()
    dates = [dct[PAIRS[0]][t]['date'] for t in num_periods]
    df['unix_date'] = pd.Series(dates)
    df['datetime'] = df['unix_date'].apply(
        lambda unix_timestamp : \
        datetime.fromtimestamp(unix_timestamp))

    # remove unneeded data
    for pair, data in dct.items():
        coin = pair[len(TETHER + '_'):]
        data2 = [data[t]['close'] for t in num_periods]
        df[coin] = pd.Series(data2)

    # save df to file
    df.to_csv(BACKTEST_DATA_FILE)

    return df

def get_past_prices_from_csv_file():

    return pd.read_csv(BACKTEST_DATA_FILE, index_col=[0])



if __name__ == '__main__':

    conn = poloniex_server()

    # variables
    startTime = datetime(2020, 2, 20, 0, 0, 0)  # year, month, day, hour, minute, second
    endTime   = datetime(2020, 2, 21, 0, 0, 0)
    # period = duration of time steps between rebalances
    #   300 s   900 s    1800 s   7200 s   14400 s   86400 s
    #   5 min   15 min   30 min   2 hrs    4 hrs     1 day
    period = 5 * 60  # duration of intervals between updates

    # determines the proper number of time steps from startTime to endTime for the given period
    num_periods = range(int((endTime - startTime).total_seconds() / period))

    # import backtest data of COIN1 and COIN2 pair
    df = get_past_prices_from_poloniex(startTime, endTime, period, num_periods, conn) \
        if QUERI_POLONIEX else get_past_prices_from_csv_file()
    # columns=[unix_date, datetime, BTC, ETH, XRP, LTC, ZEC, XMR, STR, DASH, ETC]

    # get percent change of price each time step
    # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.pct_change.html   
    df.rename(columns={coin : coin + '_price' for coin in COINS}, inplace=True)
    for coin in COINS:
        df['%s_pct_chng' % coin] = df[coin + '_price'].pct_change()
    df.drop([0], inplace=True) # remove first row (b/c it has a NaN value)
    df.reset_index(drop=True, inplace=True) # reset index accordingly
    # columns=[unix_date, datetime, BTC_price, BTC_pct_chng, ETH_price, ET_pct_chng, ... ]

    print(df)

    # # iterate over data
    # for i, row in df.iterrows():
    #     print(i)
    #     print(row)
    #     print()

    #     input()

    # can also put it all in a dct ... might be easier this way ...
    dct = {}
    for coin in COINS:
        dct[coin] = pd.DataFrame({
            'price'    : df[coin + '_price'],
            'pct_chng' : df[coin + '_pct_chng']
        })

    for coin, df in dct.items():
        print(coin)
        print(df)
        print()

    # plot pct_chng of each coin
    fig, axes = plt.subplots(3, 3, figsize=(11, 6))
    fig.suptitle('Percent Change each timestep (1.00 = 100%)')
    for i, (coin, df) in enumerate(dct.items()):
        axes[int(i / 3), i % 3].plot(df['pct_chng'])
        axes[int(i / 3), i % 3].set_title(coin)
        # axes[int(i / 3), i % 3].set_ylabel('pct_chng')
        # axes[int(i / 3), i % 3].set_xlabel('time')
    # plt.tight_layout()

    # adjust subplots and display it
    ''' https://matplotlib.org/3.1.1/api/_as_gen/matplotlib.pyplot.subplots_adjust.html
    subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=None, hspace=None)
        left  = 0.125  # the left side of the subplots of the figure                      percentage
        right = 0.9    # the right side of the subplots of the figure                     percentage
        bottom = 0.1   # the bottom of the subplots of the figure                         percentage
        top = 0.9      # the top of the subplots of the figure                            percentage
        wspace = 0.2   # the amount of width reserved for blank space between subplots    number
        hspace = 0.2   # the amount of height reserved for white space between subplots   number
        '''
    plt.subplots_adjust(
        left=0.05,
        right=0.975,
        bottom=0.05,
        wspace=0.25, hspace=0.5)
    plt.show()
