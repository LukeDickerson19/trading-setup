import time
import sys
sys.path.insert(0, './')
from poloniex import poloniex
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
pd.set_option('display.max_rows', 10)
pd.set_option('display.max_columns', 10)
# pd.set_option('display.width', 1000)
import numpy as np

''' NOTES

    DESCRIPTION:

    '''

# constants
QUERI_POLONIEX = False
BACKTEST_DATA_FILE = './price_data_one_coin.csv'
COIN1 = 'USDT'
COIN2 = 'BTC'
PAIR = COIN1 + '_' + COIN2
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

    API_KEY = '...'
    SECRET_KEY = '...'

    return poloniex(API_KEY, SECRET_KEY)


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
        prices2.append({'date': prices[t]['date'], 'price': price})

    prices3 = pd.DataFrame(prices2)
    prices3.to_csv(BACKTEST_DATA_FILE)

    return prices3

def get_past_prices_from_csv_file():

    return pd.read_csv(BACKTEST_DATA_FILE, index_col=[0])





if __name__ == '__main__':

    conn = poloniex_server()

    # variables
    startTime = datetime(2018, 3, 1, 0, 0, 0)  # year, month, day, hour, minute, second
    endTime   = datetime(2019, 5, 30, 0, 0, 0)
    # period = duration of time steps between rebalances
    #   300 s   900 s    1800 s   7200 s   14400 s   86400 s
    #   5 min   15 min   30 min   2 hrs    4 hrs     1 day
    period = 2 * 60 * 60  # duration of intervals between updates

    # determines the proper number of time steps from startTime to endTime for the given period
    num_periods = range(int((endTime - startTime).total_seconds() / period))

    # import backtest data of COIN1 and COIN2 pair
    prices = \
        get_past_prices_from_poloniex(startTime, endTime, period, num_periods, conn) \
        if QUERI_POLONIEX else get_past_prices_from_csv_file()

    # convert 'date' column from unix timestamp to datetime
    prices['date'] = prices['date'].apply(
        lambda unix_timestamp : datetime.fromtimestamp(unix_timestamp))

    # plt.plot(prices['price'])
    # plt.title('%s PriceChart' % PAIR)
    # plt.ylabel('Price')
    # plt.xlabel('Time')
    # plt.show()

    for i, row in prices.iterrows():
        date, price = row['date'], row['price']
        print(i, date, price)



        input()
