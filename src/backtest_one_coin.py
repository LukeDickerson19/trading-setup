import sys
import os
import pathlib
SCRIPT_PATH   = pathlib.Path(__file__).resolve()
ROOT_PATH     = SCRIPT_PATH.parent.parent
DATA_PATH     = os.path.join(ROOT_PATH.absolute(), 'data', 'crypto', 'poloniex')
POLONIEX_PATH = os.path.join(ROOT_PATH.absolute(), 'src', 'exchanges', 'crypto')
# print(SCRIPT_PATH.absolute())
# print(ROOT_PATH.absolute())
# print(DATA_PATH)
# print(LOG_PATH)
# print(POLONIEX_PATH)
# sys.exit()
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


''' NOTES

    TO DO
        NOW
            track p/l (quantity and percent) of open positions (which is required anyway for forced liquidation)
            unit test it
                build out and test the rest of the order functions
                    next
                        test_leverage
                            make sure all order functions work with new margin collateral vasriable
                        test_forced_liquidation
                        test_update_open_orders
                        test_trading_fee
            push it to github
            make it a parent class
            start coding strategy
        EVENTUALLY
            finish hello_world.py

    DESCRIPTION

        basic algo trading strategy setup for backtesting and live trading

    SOURCES

        none

    ALTERNATIVES:

        has shorting but doesn't have exchange and margin accounts separated
        https://github.com/enigmampc/catalyst
            Docs: https://www.enigma.co/catalyst/index.html

        has shorting but doesn't have exchange and margin accounts separated
        https://github.com/anfederico/Gemini
            docs: https://gemini-docs.readthedocs.io/en/latest/

            mean revision algo has promissing returns
                https://gemini-docs.readthedocs.io/en/latest/using-gemini.html#advanced

        https://www.reddit.com/r/algotrading/comments/bnq5cn/cryptocurrency_backtesting/
            https://gekko.wizb.it/

    '''

####################################################### CONSTANTS #######################################################

QUERI_POLONIEX = False
COIN1 = 'USDT'
COIN2 = 'BTC'
PAIR = COIN1 + '_' + COIN2
TF = 0.0025 # TF = trading fee
INCLUDE_TF = True  # flag if we want to include the TF in our calculations
MAX_LEVERAGE = 2.0

# DATA_FILENAME = 'price_data_one_coin-%s_%s-2hr_intervals-ONE_YEAR-03_01_2018_8am_to_05_30_2019_6am.csv' % (COIN2, COIN1)
# DATA_FILENAME = 'price_data_one_coin-%s_%s-5min_intervals-ONE_DAY-02-20-2020-12am_to_02-21-2020-12am.csv' % (COIN2, COIN1)
# DATA_FILENAME = 'price_data_one_coin-%s_%s-5min_intervals-ONE_MONTH-01-21-2020-12am_to_02-21-2020-12am.csv' % (COIN2, COIN1)
DATA_FILENAME = 'price_data_one_coin-%s_%s-5min_intervals-ONE_QUARTER-11-21-2019-12am_to_02-21-2020-12am.csv' % (COIN2, COIN1)
BACKTEST_DATA_FILE = os.path.join(DATA_PATH, DATA_FILENAME)


cur_pl = [0] # cur_pl = current p/l from this time step
net_pl = [0] # net_pl = net (total) p/l from the beginning of the backtest (sum of all cur_pl)
BLOCK_CUR_PL = True # set BLOCK_CUR_PL to True if you want to only update cur_pl when a trade (enter or exit) is made, else it tracks the value of the asset
BLOCK_NET_PL = True # set BLOCK_NET_PL to True if you want to only update net_pl when a trade (enter or exit) is made, else it tracks the value of the asset

# pretty print the string
# arguments:
#   string = what will be printed
#   indent = what an indent looks like
#   num_indents = number of indents to put in front of the string
#   new_line_start = print a new line in before the string
#   new_line_end = print a new line in after the string
#   draw_line = draw a line on the blank line before or after the string
# pprint constants
OUTPUT_TO_CONSOLE = True
OUTPUT_TO_LOGFILE = True
STRATEGY_LOGFILE_PATH  = os.path.join(ROOT_PATH.absolute(), 'logs', 'backtest_log.txt')
UNITTEST_LOGFILE_PATH  = os.path.join(ROOT_PATH.absolute(), 'logs', 'unittest_log.txt')
LOGFILE_PATH = None # to be set by Strat class or StratUnitTests class
INDENT = '|   '
DRAW_LINE = False

#########################################################################################################################



class Strat:

    # create strategy instance
    def __init__(self,
        backtesting=True,
        verbose=False,
        num_indents=0,
        logfile_path=STRATEGY_LOGFILE_PATH,
        clear_log=True):

        self.logfile_path = logfile_path
        if clear_log:
            open(self.logfile_path, 'w').close()
        if verbose: self.pprint('Initializing Strategy ...', num_indents=num_indents)

        exchange_start_quantity, margin_start_quantity = \
            self.setup_backtesting(verbose=verbose, num_indents=num_indents+1) \
            if backtesting else \
            self.setup_livetrading(verbose=verbose, num_indents=num_indents+1)

        self.portfolio_init = {
            'exchange' : {
                COIN1 : exchange_start_quantity,  # initial quantity of money (in COIN1) in the Exchange account
                COIN2 : 0.0                       # initial quantity of money (in COIN2) in the Exchange account
            },
            'margin' : {
                'collateral' : margin_start_quantity,         # initial quantity of money (in COIN1) in the Margin account (aka collateral)
                'debt': {COIN1 : 0.0, COIN2 : 0.0}            # initial quantity of money in the Margin account that has been borrowed
                COIN1 : margin_start_quantity * MAX_LEVERAGE, # initial quantity of money (in COIN1) in Margin account that can be borrowed
                COIN2 : 0.0                                   # initial quantity of money (in COIN2) in the Margin account (+ is long, - is short)
            }
        }
        self.portfolio = {
            'exchange' : {
                COIN1 : [self.portfolio_init['exchange'][COIN1]], # current quantity of money (in COIN1) in the Exchange account
                COIN2 : [self.portfolio_init['exchange'][COIN2]]  # current quantity of money (in COIN2) in the Exchange account
            },
            'margin' : {
                'collateral' : [self.portfolio_init['margin']['collateral']], # current quantity of money (in COIN1) in the Margin account (aka collateral)
                'debt'       : [self.portfolio_init['margin']['debt']],       # current quantity of money in the Margin account that has been borrowed
                COIN1        : [self.portfolio_init['margin'][COIN1]],        # current quantity of money (in COIN1) in Margin account that can be borrowed
                COIN2        : [self.portfolio_init['margin'][COIN2]]         # current quantity of money (in COIN2) in the Margin account (+ is long, - is short)
            }
        }
        self.portfolio_update_reset()
        self.open_orders = {}
        # dict:
        # key = order_id
        # value = [account_type(str), long_or_short(str), enter_or_exit(str), quantity(float), limit_price(float), percent(boolean)]
        # self.open_positions = {
        #     'exchange' : [],
        #     'margin' :   []
        # }
        # # dict:
        # # value: (dict with keys): long_or_short(str), quantity(float), enter_price(float)
        self.margin_coin1_debt

        self.reset(
            exchange_start_quantity,
            margin_start_quantity,
            verbose=verbose,
            num_indents=num_indents)
        if verbose: self.pprint('Strategy Initialized.', num_indents=num_indents)

    # create strategy setup
    def setup_livetrading(self,
        verbose=False,
        num_indents=0):
    
        if verbose: self.pprint('Initializing Live Trading ...', num_indents=num_indents)
        
        self.conn = self.poloniex_server() # TODO: make this class exchange agnostic. requires ExchangeAPIWrapper super class and child classes for each exchange (either type: 'crypto', 'stocks'). OR! make it so this class can trade on multiple exchanges
        self.date = datetime.now(timezone.utc)
        self.unix_date = time.mktime(self.date.timetuple())
        self.price = 0 #self.conn.get_current_price(COIN1, COIN2) # tbd
        self.pct_chg = 0 #self.conn.get_pct_chg(COIN1, COIN2, period)
        exchange_start_quantity = 0 # TODO: get COIN1 quantity on Exchange account
        margin_start_quantity   = 0 # TODO: get COIN1 quantity on Margin account
        if verbose:
            self.pprint('t:         %d' % self.t,         num_indents=num_indents+1)
            self.pprint('unix_date: %s' % self.unix_date, num_indents=num_indents+1)
            self.pprint('date:      %s' % self.date,      num_indents=num_indents+1)
            self.pprint('price:     %s' % self.price,     num_indents=num_indents+1)
            self.pprint('pct_chg:   %s' % self.pct_chg,   num_indents=num_indents+1)
            self.pprint('Live Trading Initialized.',      num_indents=num_indents)
        return exchange_start_quantity, margin_start_quantity
    def setup_backtesting(self,
        exchange_start_quantity=50000.0,
        margin_start_quantity=50000.0,
        start_time_dt=datetime(2019, 11, 21, 0, 0, 0),  # year, month, day, hour, minute, second
        end_time_dt=datetime(  2020,  2, 21, 0, 0, 0),
        period= 5 * 60, # 5 min intervals between timesteps
        t=0, # timestep to start strategy at
        verbose=True,
        num_indents=0):

        if verbose: self.pprint('Initializing Backtesting ...', num_indents=num_indents)

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
        self.num_periods = int((end_time_dt - start_time_dt).total_seconds() / period)

        if verbose:
            self.pprint('Exchange Start Quantity ............ %.6f %s' % (exchange_start_quantity, COIN1),   num_indents=num_indents+1)
            self.pprint('Margin Start Quantity .............. %.6f %s' % (margin_start_quantity, COIN1),     num_indents=num_indents+1)
            self.pprint('Start Time ......................... %s' % start_time_dt.strftime('%Y-%m-%d-%I%p'), num_indents=num_indents+1)
            self.pprint('End Time ........................... %s' % end_time_dt.strftime('%Y-%m-%d-%I%p'),   num_indents=num_indents+1)
            self.pprint('Time Step Duration ................. %s' % period_labels[period],                   num_indents=num_indents+1)
            self.pprint('Total Number of Time Steps ......... %d' % self.num_periods,                        num_indents=num_indents+1) 

        # import backtest price data of COIN1 and COIN2 pair
        df = \
            self.get_past_prices_from_poloniex(
                start_time_dt,
                end_time_dt,
                period,
                self.num_periods,
                verbose=verbose,
                num_indends=num_indends+1) \
            if QUERI_POLONIEX else \
            self.get_past_prices_from_csv_file(
                verbose=verbose, num_indents=num_indents+1)

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

        self.df = df
        self.t = t
        self.unix_date, self.date, self.price, self.pct_chg = df.iloc[t]
        if verbose:
            self.pprint('Starting Backtest at:', num_indents=num_indents+1)
            self.pprint('t ....................................... %d' % self.t,                                num_indents=num_indents+2)
            self.pprint('unix_date ............................... %s' % self.unix_date,                        num_indents=num_indents+2)
            self.pprint('date .................................... %s' % self.date,                             num_indents=num_indents+2)
            self.pprint('price ................................... %s %s per %s' % (self.price, COIN1, COIN2),  num_indents=num_indents+2)
            label = '%s) %s %.4f %%' % (
                period_labels[period],
                (16 - len(period_labels[period])) * '.',
                (100 * self.pct_chg))
            self.pprint('pct_chg (from previous %s' % label,                                                    num_indents=num_indents+2)
            self.pprint('Backtesting Initialized.',      num_indents=num_indents)
        return exchange_start_quantity, margin_start_quantity
    def reset(self,
        exchange_start_quantity,
        margin_start_quantity,
        verbose=False,
        num_indents=0):

        ########################################################## STRATEGY INIT GOES HERE #####################################################

        # tbd
        pass

        ########################################################################################################################################
    def portfolio_update_reset(self,
        verbose=False, num_indents=0):
        
        if verbose: self.pprint('Setting portfolio_update to zero.', num_indents=num_indents)
        self.portfolio_update = {
            'exchange' : {
                COIN1 : 0.0,
                COIN2 : 0.0
            },
            'margin' : {
                'collateral' : 0.0,
                COIN1        : 0.0,
                COIN2        : 0.0
            }
        }
        if verbose: self.pprint('Successful.', num_indents=num_indents)
    def pprint(self, string='',
        num_indents=0,
        new_line_start=False,
        new_line_end=False):

        def output(out_loc):
            indent = len(INDENT)*' ' if out_loc != sys.stdout else INDENT
            total_indent0 = ''.join([indent] * num_indents)
            total_indent1 = ''.join([indent] * (num_indents + 1))
            if new_line_start:
                print(total_indent1 if DRAW_LINE else total_indent0, file=out_loc)
            for s in string.split('\n'):
                print(total_indent0 + s, file=out_loc)
            if new_line_end:
                print(total_indent1 if DRAW_LINE else total_indent0, file=out_loc)

        if OUTPUT_TO_CONSOLE:
            output(sys.stdout)
        if OUTPUT_TO_LOGFILE:
            logfile = open(self.logfile_path, 'a')
            output(logfile)
            logfile.close()

    # connect to Poloniex Exchange server
    def poloniex_server(self):

        # select which account to use:
        account = 'account1'

        data       = json.load(open('./api_keys.json', 'r'))
        api_key    = data['exchanges']['poloniex'][account]['api_key']
        secret_key = data['exchanges']['poloniex'][account]['secret_key']

        return Poloniex(api_key, secret_key)

    # get backtesting data
    def get_past_prices_from_poloniex(self,
        start_time_dt,
        end_time_dt,
        period,
        num_periods,
        save_to_csv=False,
        verbose=False,
        num_indents=0):

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

        if verbose: self.pprint('Successfully aquired price data from poloniex API.', num_indents=num_indents, new_line_start=True)
        return df
    def get_past_prices_from_csv_file(self,
        verbose=False,
        num_indents=0):
        if verbose: self.pprint('Successfully aquired price data from CSV file.', num_indents=num_indents, new_line_start=True)
        return pd.read_csv(BACKTEST_DATA_FILE, index_col=[0])

    # run backtest
    def backtest(self):

        # iterate over each timestep starting at t
        while self.t < self.num_periods:
            self.t += 1
            self.update()
            input()
        print('Backtest Complete')
    def update(self,
        verbose=False,
        num_indents=0):

        self.unix_date, self.date, self.price, self.pct_chg = self.df.iloc[self.t]
        t, unix_date, date, price, pct_chg = self.t, self.unix_date, self.date, self.price, self.pct_chg
        # if verbose: self.pprint('%d   %s   %s   %.6f %s/%s    %.1f %%' % (
        #     t, unix_date, date, price, COIN1, COIN2, (100*pct_chg)), num_indents=num_indents)

        self.pprint('Updating Backtest', num_indents=num_indents)
        if verbose:
            self.pprint('t ..................... %s' % t, num_indents=num_indents+1)
            self.pprint('unix_date ............. %s' % unix_date, num_indents=num_indents+1)
            self.pprint('date .................. %s' % date, num_indents=num_indents+1)
            self.pprint('price ................. %.6f %s/%s' % (price, COIN1, COIN2), num_indents=num_indents+1)
            self.pprint('pct_chg ............... %.1f %%' % (100*pct_chg), num_indents=num_indents+1)


        self.check_for_forced_liquidation(verbose=verbose, num_indents=num_indents)

        ########################################################## STRATEGY UPDATE GOES HERE ###################################################

        # tbd

        ########################################################################################################################################

        self.pprint('', num_indents=num_indents+1)
        self.execute_net_trades(verbose=verbose, num_indents=num_indents+1)

        self.pprint('Update Complete.', num_indents=num_indents)

    # place order
    def order(self,
        exchange_or_margin,
        enter_or_exit,
        long_or_short,
        quantity,
        percent=False,
        limit_price=None,
        verbose=False,
        num_indents=0):

        if exchange_or_margin == 'exchange':
            return self.exchange_order(
                enter_or_exit, long_or_short, quantity,
                percent=percent, limit_price=limit_price,
                verbose=verbose, num_indents=num_indents)
        elif exchange_or_margin == 'margin':
            return self.margin_order(
                enter_or_exit, long_or_short, quantity,
                leverage=leverage, percent=percent, limit_price=limit_price,
                verbose=verbose, num_indents=num_indents)
        else:
            return None, 'Invalid input for exchange_or_margin'
    def exchange_order(self,
        enter_or_exit,
        long_or_short,
        quantity,
        percent=False,
        limit_price=None,
        verbose=False,
        num_indents=0):
        
        if enter_or_exit == 'enter':
            if long_or_short == 'long':
                return self.enter_long(
                    'exchange', quantity,
                    percent=percent, limit_price=limit_price,
                    verbose=verbose, num_indents=num_indents)
            else:
                return None, 'Invalid input for long_or_short'
        elif enter_or_exit == 'exit':
            if long_or_short == 'long':
                return self.exit_long(
                    'exchange', quantity,
                    percent=percent, limit_price=limit_price,
                    verbose=verbose, num_indents=num_indents)
            else:
                return None, 'Invalid input for long_or_short'
        else:
            return None, 'Invalid input for enter_or_exit'
    def margin_order(self,
        enter_or_exit,
        long_or_short,
        quantity,
        percent=False,
        limit_price=None,
        verbose=False,
        num_indents=0):

        # if enter long order and we're currently short
        if enter_or_exit == 'enter':
            if long_or_short == 'long':
                pass
                # if we're currently short
                    # if quantity is less than or equal to quantity that we're in short
                        # exit that quantity of the short
                    # else its more
                        # exit our short position entirely and enter long the difference

            elif long_or_short == 'short':
                pass
                # if we're currently long
                    # if quantity is less than or equal to quantity that we're in long
                        # exit that quantity of the long
                    # else its more
                        # exit our long position entirely and enter short the difference

        if enter_or_exit == 'enter':
            if long_or_short == 'long':
                return self.enter_long(
                    'margin', quantity,
                    percent=percent, limit_price=limit_price,
                    verbose=verbose, num_indents=num_indents)
            elif long_or_short == 'short':
                return self.enter_short(
                    'margin', quantity,
                    percent=percent, limit_price=limit_price,
                    verbose=verbose, num_indents=num_indents)
            else:
                return None, 'Invalid input for long_or_short'
        elif enter_or_exit == 'exit':
            if long_or_short == 'long':
                return self.exit_long(
                    'margin', quantity,
                    percent=percent, limit_price=limit_price,
                    verbose=verbose, num_indents=num_indents)
            elif long_or_short == 'short':
                return self.exit_short(
                    'margin', quantity,
                    percent=percent, limit_price=limit_price,
                    verbose=verbose, num_indents=num_indents)
            else:
                return None, 'Invalid input for long_or_short'
        else:
            return None, 'Invalid input for enter_or_exit'

    # execute long orders
    def enter_long(self,
        account_type,
        quantity,
        percent=False,
        limit_price=None,
        verbose=False,
        num_indents=0):

        if limit_price == None: # market order
            return self.enter_long_market_order(
                account_type, quantity, percent=percent,
                verbose=verbose, num_indents=num_indents)
        elif isinstance(limit_price, float): # limit order
            return self.enter_long_limit_order(
                account_type, quantity, limit_price, percent=percent,
                verbose=verbose, num_indents=num_indents)
        else:
            return None, 'Invalid input for limit_price'
    def enter_long_market_order(self,
        account_type,
        quantity,
        percent=False,
        verbose=False,
        num_indents=0):

        self.pprint('Entering Long Market Order', num_indents=num_indents)
        if verbose:
            self.pprint('account_type .......... %s' % account_type, num_indents=num_indents+1)
            self.pprint('percent ............... %s' % percent, num_indents=num_indents+1)
            self.pprint('quantity .............. %s %s' % (
                (100*quantity) if percent else quantity,
                '%' if percent else COIN2),
                num_indents=num_indents+1)

        # if percent: 'quantity' is a percent (0.00 to 1.00)
        # determine the actual quantity of COIN1 of portfolio in account_type to a quantity of COIN2
        if percent:
            quantity = self.convert_percent_to_quantity(
                account_type, COIN1, COIN2, quantity,
                verbose=verbose, num_indents=num_indents+1)

        # exit short if theres anything short
        quantity_short = self.portfolio['margin'][COIN2][-1]
        if account_type == 'margin' and quantity_short < 0:
            if quantity <= abs(quantity_short):
                self.pprint('Currently short %.6f %s. Converting enter long to exit short' % (
                    quantity_short, COIN2), num_indents=num_indents+1, new_line_start=True)
                _, trade_message = self.exit_short_market_order(
                    account_type,
                    quantity,
                    verbose=verbose,
                    num_indents=num_indents+1)
                quantity = 0
            else: # quantity > quantity_short
                self.pprint('Currently short %.6f %s. Exiting short and decreasing quantity' % (
                    quantity_short, COIN2), num_indents=num_indents+1, new_line_start=True)
                self.exit_short_market_order(
                    account_type,
                    abs(quantity_short),
                    verbose=verbose,
                    num_indents=num_indents+1)
                quantity -= abs(quantity_short)
                self.pprint('quantity decreased to %.6f %s' % (
                    quantity, COIN2), num_indents=num_indents+1)

        if quantity > 0:
            coin1_cost = quantity * self.price # trading fee is not added back on here because thats done in the transfer function
            coin2_gain = quantity
            _, trade_message = self.trade(account_type, COIN1, coin1_cost, COIN2, coin2_gain, verbose=verbose, num_indents=num_indents+1)
            # self.open_positions[account_type].append({
            #     'long_or_short' : 'short',
            #     'coin1_cost'    : coin1_cost,
            #     'quantity'      : quantity,
            #     'enter_price'   : self.price
            # })
            self.open_positions_total_coin1_cost += coin1_cost

        self.pprint('Enter Long %s.' % ('Succeeded' if trade_message == 'Trade Successful.' else 'Failed'), num_indents=num_indents)
        return None, trade_message
    def enter_long_limit_order(self,
        account_type,
        quantity,
        limit_price,
        percent=False,
        verbose=False,
        num_indents=0):

        self.pprint('Entering Long Limit Order', num_indents=num_indents)
        if verbose:
            self.pprint('account_type .......... %s' % account_type, num_indents=num_indents+1)
            self.pprint('percent ............... %s' % percent, num_indents=num_indents+1)
            self.pprint('quantity .............. %s %s' % (
                (100*quantity) if percent else quantity,
                '%' if percent else COIN2),
                num_indents=num_indents+1)
            self.pprint('limit_price ........... %s %s/%s' % (limit_price, COIN1, COIN2), num_indents=num_indents+1)

        if limit_price >= self.price:
            if verbose: self.pprint('\nlimit_price is more than current price of %.6f %s/%s, entering at current price ...' % (
                    self.price, COIN1, COIN2), num_indents=num_indents+1)
            order_id, trade_message = self.enter_long_market_order(
                account_type, quantity, percent=percent, verbose=verbose, num_indents=num_indents+1)
            if verbose: self.pprint('Enter Limit Long %s.' % ('Succeeded' if trade_message == 'Trade Successful.' else 'Failed'), num_indents=num_indents)
            return order_id, trade_message
        else:
            order_id = self.get_order_id()
            self.open_orders[order_id] = [account_type, 'long', 'enter', quantity, limit_price, percent]
            if verbose: self.pprint('Created enter long open limit order. order_id: %s' % order_id, num_indents=num_indents)
            return order_id, 'Created enter long open limit order'
    def exit_long(self,
        account_type,
        quantity,
        percent=False,
        limit_price=None,
        verbose=False,
        num_indents=0):

        if limit_price == None: # market order
            return self.exit_long_market_order(
                account_type, quantity, percent=percent,
                verbose=verbose, num_indents=num_indents)
        elif isinstance(limit_price, float): # limit order
            return self.exit_long_limit_order(
                account_type, quantity, limit_price, percent=percent,
                verbose=verbose, num_indents=num_indents)
        else:
            return None, 'Invalid input for limit_price'
    def exit_long_market_order(self,
        account_type,
        quantity,
        percent=False,
        verbose=False,
        num_indents=0):

        self.pprint('Exiting Long Market Order', num_indents=num_indents)
        if verbose:
            self.pprint('account_type .......... %s' % account_type, num_indents=num_indents+1)
            self.pprint('percent ............... %s' % percent, num_indents=num_indents+1)
            self.pprint('quantity .............. %s %s' % (
                (100*quantity) if percent else quantity,
                '%' if percent else COIN2),
                num_indents=num_indents+1)

        # if percent: 'quantity' is a percent (0.00 to 1.00)
        # determine the actual quantity of COIN1 of portfolio in account_type to a quantity of COIN2
        if percent:
            quantity = self.convert_percent_to_quantity(
                account_type, COIN2, COIN2, quantity,
                deduct_tf=False, verbose=verbose, num_indents=num_indents+1)

        coin2_cost = quantity
        coin1_gain = quantity * self.price
        order_id, trade_message = self.trade(account_type, COIN2, coin2_cost, COIN1, coin1_gain, verbose=verbose, num_indents=num_indents)

        # # update collateral (with portfolio update) <-- this requires tracking open positions (which is required anyway for forced liquidation)
        # if trade_message == 'Trade Successful.' and account_type == 'margin':
        #     for op in self.open_positions[account_type]:
        #         op['long_or_short']
        #         op['quantity']
        #         op['enter_price']

        return None, trade_message
    def exit_long_limit_order(self,
        account_type,
        quantity,
        limit_price,
        percent=False,
        verbose=False,
        num_indents=0):

        self.pprint('Exiting Long Limit Order', num_indents=num_indents)
        if verbose:
            self.pprint('account_type .......... %s' % account_type, num_indents=num_indents+1)
            self.pprint('percent ............... %s' % percent, num_indents=num_indents+1)
            self.pprint('quantity .............. %s %s' % (
                (100*quantity) if percent else quantity,
                '%' if percent else COIN2),
                num_indents=num_indents+1)
            self.pprint('limit_price ........... %s %s/%s' % (limit_price, COIN1, COIN2), num_indents=num_indents+1)

        if limit_price <= self.price:
            if verbose: self.pprint('\nlimit_price is less than current price of %.6f %s/%s, exiting at current price ...' % (
                    self.price, COIN1, COIN2), num_indents=num_indents+1)
            order_id, trade_message = self.exit_long_market_order(
                account_type, quantity, percent=percent, verbose=verbose, num_indents=num_indents+1)
            if verbose: self.pprint('Exit Limit Long %s.' % ('Succeeded' if trade_message == 'Trade Successful.' else 'Failed'), num_indents=num_indents)
            return order_id, trade_message
        else:
            order_id = self.get_order_id()
            self.open_orders[order_id] = [account_type, 'long', 'exit', quantity, limit_price, percent]
            if verbose: self.pprint('Created exit long open limit order. order_id: %s' % order_id, num_indents=num_indents)
            return order_id, 'Created exit long open limit order'

    # execute short orders
    def enter_short(self,
        account_type,
        quantity,
        percent=False,
        limit_price=None,
        verbose=False,
        num_indents=0):

        if limit_price == None: # market order
            return self.enter_short_market_order(
                account_type, quantity, percent=percent,
                verbose=verbose, num_indents=num_indents)
        elif isinstance(limit_price, float): # limit order
            return self.enter_short_limit_order(
                account_type, quantity, limit_price, percent=percent,
                verbose=verbose, num_indents=num_indents)
        else:
            return None, 'Invalid input for limit_price'
    def enter_short_market_order(self,
        account_type,
        quantity,
        percent=False,
        verbose=False,
        num_indents=0):

        self.pprint('Entering Short Market Order', num_indents=num_indents)
        if verbose:
            self.pprint('account_type .......... %s' % account_type, num_indents=num_indents+1)
            self.pprint('percent ............... %s' % percent, num_indents=num_indents+1)
            self.pprint('quantity .............. %s %s' % (
                (100*quantity) if percent else quantity,
                '%' if percent else COIN2),
                num_indents=num_indents+1)

        # if percent: 'quantity' is a percent (0.00 to 1.00)
        # determine the actual quantity of COIN1 of portfolio in account_type to a quantity of COIN2
        if percent:
            quantity = self.convert_percent_to_quantity(
                account_type, COIN1, COIN2, quantity,
                verbose=verbose, num_indents=num_indents+1)

        # exit long if theres anything long
        quantity_long = self.portfolio['margin'][COIN2][-1]
        if account_type == 'margin' and quantity_long > 0:
            if quantity <= quantity_long:
                self.pprint('Currently long %.6f %s. Converting enter short to exit long' % (
                    quantity_long, COIN2), num_indents=num_indents+1, new_line_start=True)
                _, trade_message = self.exit_long_market_order(
                    account_type,
                    quantity,
                    verbose=verbose,
                    num_indents=num_indents+1)
                quantity = 0
            else: # quantity > quantity_long
                self.pprint('Currently long %.6f %s. Exiting long and decreasing quantity' % (
                    quantity_long, COIN2), num_indents=num_indents+1, new_line_start=True)
                self.exit_long_market_order(
                    account_type,
                    quantity_long,
                    verbose=verbose,
                    num_indents=num_indents+1)
                quantity -= quantity_long
                self.pprint('quantity decreased to %.6f %s' % (
                    quantity, COIN2), num_indents=num_indents+1)

        if quantity > 0:
            coin1_cost = quantity * self.price # trading fee is not added back on here because thats done in the transfer function
            coin2_gain = -quantity # NOTE: when you enter a short, COIN2 in the margin account goes - (or subtracts from a previously + value)
            _, trade_message = self.trade(account_type, COIN1, coin1_cost, COIN2, coin2_gain, verbose=verbose, num_indents=num_indents+1)
            # self.open_positions[account_type].append({
            #     'long_or_short' : 'short',
            #     'coin1_cost'    : coin1_cost,
            #     'quantity'      : quantity,
            #     'enter_price'   : self.price
            # })
            self.open_positions_total_coin1_cost += coin1_cost
            
        self.pprint('Enter Short %s.' % ('Succeeded' if trade_message == 'Trade Successful.' else 'Failed'), num_indents=num_indents)
        return None, trade_message
    def enter_short_limit_order(self,
        account_type,
        quantity,
        limit_price,
        percent=False,
        verbose=False,
        num_indents=0):

        self.pprint('Entering Short Limit Order', num_indents=num_indents)
        if verbose:
            self.pprint('account_type .......... %s' % account_type, num_indents=num_indents+1)
            self.pprint('percent ............... %s' % percent, num_indents=num_indents+1)
            self.pprint('quantity .............. %s %s' % (
                (100*quantity) if percent else quantity,
                '%' if percent else COIN2),
                num_indents=num_indents+1)
            self.pprint('limit_price ........... %s %s/%s' % (limit_price, COIN1, COIN2), num_indents=num_indents+1)

        if limit_price <= self.price:
            if verbose: self.pprint('\nlimit_price is less than current price of %.6f %s/%s, entering at current price ...' % (
                    self.price, COIN1, COIN2), num_indents=num_indents+1)
            order_id, trade_message = self.enter_short_market_order(
                account_type, quantity, percent=percent, verbose=verbose, num_indents=num_indents+1)
            if verbose: self.pprint('Enter Limit Short %s.' % ('Succeeded' if trade_message == 'Trade Successful.' else 'Failed'), num_indents=num_indents)
            return order_id, trade_message
        else:
            order_id = self.get_order_id()
            self.open_orders[order_id] = [account_type, 'short', 'enter', quantity, limit_price, percent]
            if verbose: self.pprint('Created enter short open limit order. order_id: %s' % order_id, num_indents=num_indents)
            return order_id, 'Created enter short open limit order'
    def exit_short(self,
        account_type,
        quantity,
        percent=False,
        limit_price=None,
        verbose=False,
        num_indents=0):

        if limit_price == None: # market order
            return self.exit_short_market_order(
                account_type, quantity, percent=percent,
                verbose=verbose, num_indents=num_indents)
        elif isinstance(limit_price, float): # limit order
            return self.exit_short_limit_order(
                account_type, quantity, limit_price, percent=percent,
                verbose=verbose, num_indents=num_indents)
        else:
            return None, 'Invalid input for limit_price'
    def exit_short_market_order(self,
        account_type,
        quantity,
        percent=False,
        verbose=False,
        num_indents=0):

        self.pprint('Exiting Short Market Order', num_indents=num_indents)
        if verbose:
            self.pprint('account_type .......... %s' % account_type, num_indents=num_indents+1)
            self.pprint('percent ............... %s' % percent, num_indents=num_indents+1)
            self.pprint('quantity .............. %s %s' % (
                (100*quantity) if percent else quantity,
                '%' if percent else COIN2),
                num_indents=num_indents+1)

        # if percent: 'quantity' is a percent (0.00 to 1.00)
        # determine the actual quantity of COIN1 of portfolio in account_type to a quantity of COIN2
        if percent:
            quantity = self.convert_percent_to_quantity(
                account_type, COIN2, COIN2, quantity,
                deduct_tf=False, verbose=verbose, num_indents=num_indents+1)
        
        # all_open_positions_total_coin1_cost is used later but it needs to go before self.trade
        # because self.trade changes portfolio COIN1 value
        all_open_positions_total_coin1_cost = \
            (self.portfolio[account_type]['collateral'] * MAX_LEVERAGE) - \
            self.portfolio[account_type][COIN1]

        coin2_cost = -quantity # NOTE: when you exit a short, COIN2 in the margin account increases (adds to a previously - value)
        coin1_gain = quantity * self.price
        order_id, trade_message = self.trade(account_type, COIN2, coin2_cost, COIN1, coin1_gain, verbose=verbose, num_indents=num_indents)

        # update collateral (with portfolio update) <-- this requires tracking open positions coin1 cost (which is required anyway for forced liquidation)
        if trade_message == 'Trade Successful.' and account_type == 'margin':

            self.portfolio_update[account_type]['collateral'] += (coin1_gain - op['coin1_cost'])

            op_i = 0
            _coin2_cost = abs(coin2_cost)
            indeces_of_open_positions_to_close = []
            index_of_open_position_to_partially_close = None
            net_original_coin1_cost = 0
            for op_i, op in enumerate(self.open_positions[account_type]):
                # _coin2_cost is >, =, or < quantity of op
                if _coin2_cost >= op['quantity']:
                    indeces_of_open_positions_to_close.append(op_i)
                    net_original_coin1_cost += op['coin1_cost']
                else: # _coin2_cost < op['quantity']
                    index_of_open_position_to_partially_close = op_i
                    net_original_coin1_cost += 
                _coin2_cost -= op['quantity']

            # update collateral
            _coin1_gain = coin1_gain
            for op_i in indeces_of_open_positions_to_close:
                op = self.open_positions[account_type][op_i]
            self.portfolio_update[account_type]['collateral'] += (coin1_gain - op['coin1_cost'])

            # update partial one

            # exit ones to close


        return None, trade_message
    def exit_short_limit_order(self,
        account_type,
        quantity,
        limit_price,
        percent=False,
        verbose=False,
        num_indents=0):

        self.pprint('Exiting Short Limit Order', num_indents=num_indents)
        if verbose:
            self.pprint('account_type .......... %s' % account_type, num_indents=num_indents+1)
            self.pprint('percent ............... %s' % percent, num_indents=num_indents+1)
            self.pprint('quantity .............. %s %s' % (
                (100*quantity) if percent else quantity,
                '%' if percent else COIN2),
                num_indents=num_indents+1)
            self.pprint('limit_price ........... %s %s/%s' % (limit_price, COIN1, COIN2), num_indents=num_indents+1)

        if limit_price >= self.price:
            if verbose: self.pprint('\nlimit_price is more than current price of %.6f %s/%s, exiting at current price ...' % (
                    self.price, COIN1, COIN2), num_indents=num_indents+1)
            order_id, trade_message = self.exit_short_market_order(
                account_type, quantity, percent=percent, verbose=verbose, num_indents=num_indents+1)
            if verbose: self.pprint('Exit Limit Short %s.' % ('Succeeded' if trade_message == 'Trade Successful.' else 'Failed'), num_indents=num_indents)
            return order_id, trade_message
        else:
            order_id = self.get_order_id()
            self.open_orders[order_id] = [account_type, 'short', 'exit', quantity, limit_price, percent]
            if verbose: self.pprint('Created exit short open limit order. order_id: %s' % order_id, num_indents=num_indents)
            return order_id, 'Created exit short open limit order'

    # order helper functions
    def trade(self,
        account_type,
        from_key,
        from_cost,
        to_key,
        to_gain,
        verbose=False,
        num_indents=0):
        '''
            if enter long:  from_cost is +, to_gain is +
            if enter short: from_cost is +, to_gain is -
            if exit long:   from_cost is +, to_gain is +
            if exit short:  from_cost is -, to_gain is + 
            regardless of account_type (cause only 'margin' can short)

            '''

        # 
        if from_key == COIN1: from_cost *= 1 + (TF if INCLUDE_TF else 0)
        elif to_key == COIN1: to_gain /= 1 + (TF if INCLUDE_TF else 0)
        if verbose: self.pprint('Trading %.6f %s for %.6f %s' % (from_cost, from_key, to_gain, to_key), num_indents=num_indents)

        # if they can afford the cost
        from_account_value = (
            self.portfolio[account_type][from_key][-1] + \
            self.portfolio_update[account_type][from_key]) * \
            (MAX_LEVERAGE if account_type == 'margin' and from_key == COIN1 else 1)
        if abs(from_account_value) >= abs(from_cost):

            # subtract the cost from their from_account
            self.portfolio_update[account_type][from_key] -= from_cost

            # add the gain to their to_account
            self.portfolio_update[account_type][to_key] += to_gain # to_gain is + if long trade, and - if short trade

            if verbose: self.pprint('Trade Successful.', num_indents=num_indents)
            message = 'Trade Successful.'

        else:
            if verbose: self.pprint('Cannot afford trade. Own %.6f %s' % (from_account_value, from_key), num_indents=num_indents)
            message = 'Could not afford trade.'

        if message == 'Trade Successful' and account_type == 'margin':
            if from_key == COIN1: # enter and new debt
                self.portfolio_update[account_type]['debt'] += from_cost

            elif from_key == COIN2: # exit and update collateral
                self.portfolio_update[account_type]['debt'][COIN?] += 
                self.portfolio_update[account_type]['collateral'] += 

        return None, message
    def convert_percent_to_quantity(self,
        account_type,
        from_key,
        to_key,
        percent,
        deduct_tf=True,
        verbose=False,
        num_indents=0):

        if verbose: self.pprint('converting %.1f %% of %s supply to desired quantity of %s ...' % (100*percent, from_key, to_key), num_indents=num_indents)
        from_account_value = self.portfolio[account_type][from_key][self.t] + self.portfolio_update[account_type][from_key]
        
        quantity0 = percent * abs(from_account_value) # convert from percentage to quantity of from_key
        if verbose: self.pprint('%.1f %% of the %.6f %s supply is ......... %.6f %s' % (
            (100*percent), from_account_value, from_key, quantity0, from_key), num_indents=num_indents+1)
        
        if from_key != to_key: # this occurs when its an enter order
            if from_key == COIN1: quantity = quantity0 / self.price # convert from quantity of COIN1 to quantity of COIN2
            elif to_key == COIN2: quantity = quantity0 * self.price # convert from quantity of COIN2 to quantity of COIN1
            if verbose: self.pprint('%.6f %s at %.6f %s/%s is ...... %.6f %s' % (
                quantity0, from_key, self.price, COIN1, COIN2, quantity, to_key), num_indents=num_indents+1)
        else: # this occurs when its an exit order
            quantity = quantity0

        # factor in trading fee
        if deduct_tf:
            quantity /= (1 + (TF if INCLUDE_TF else 0))
            if verbose: self.pprint('quantity of %s (post trading fee) ................ %.6f %s' % (
                to_key, quantity, to_key), num_indents=num_indents+1)

        return quantity
    def get_order_id(self):
        i = 0
        for order_id in self.open_orders.keys():
            if order_id > i:
                return i
            else:
                i += 1
        return i

    def execute_net_trades(self,
        verbose=False,
        num_indents=0):
        if verbose: self.pprint('Executing Net Trades of t=%d' % self.t, num_indents=num_indents)

        zero_trades = 0
        for account_type in ['exchange', 'margin']:
            for asset in ['collateral', COIN1, COIN2]:
                if account_type == 'exchange' and asset == 'collateral': continue # skip this combo b/c it doesn't exist

                if self.portfolio_update[account_type][asset] != 0:
                    if verbose: self.pprint('BEFORE: %.6f %s in %s account' % (
                        self.portfolio[account_type][asset][-1],
                        asset, account_type), num_indents=num_indents+1)

                    self.portfolio[account_type][asset].append(
                        self.portfolio[account_type][asset][-1] + \
                        self.portfolio_update[account_type][asset])

                    if verbose: self.pprint('AFTER:  %.6f %s in %s account' % (
                        self.portfolio[account_type][asset][-1],
                        asset, account_type), num_indents=num_indents+1)
                else:
                    zero_trades += 1
        if verbose: self.pprint('Successful%s.' % (
            ', no trades to execute' if zero_trades == 4 else ''),
            num_indents=num_indents)

        self.portfolio_update_reset(
            verbose=verbose,
            num_indents=num_indents)
    def check_for_forced_liquidation(self,
        verbose=False, num_indents=0):
        
        # if losses are greater than collateral
            # do a forced liqidation
        pass



def run_unittests(verbose=False):
    open(UNITTEST_LOGFILE_PATH, 'w').close() # clear log
    test = StratUnitTests()
    test.pprint('Running Unit Tests:', num_indents=0)

    test.test_enter_long_market_order(verbose=verbose,  num_indents=1)
    test.test_enter_short_market_order(verbose=verbose, num_indents=1)

    test.test_convert_enter_to_exit_opposite(verbose=verbose, num_indents=1)

    test.test_exit_long_market_order(verbose=verbose,   num_indents=1)
    test.test_exit_short_market_order(verbose=verbose,  num_indents=1)

    test.test_enter_long_limit_order(verbose=verbose, num_indents=1)
    test.test_enter_short_limit_order(verbose=verbose, num_indents=1)

    test.test_exit_long_limit_order(verbose=verbose, num_indents=1)
    test.test_exit_short_limit_order(verbose=verbose, num_indents=1)

    test.test_convert_enter_to_exit_opposite(verbose=verbose, num_indents=1)

    test.test_leverage(verbose=verbose, num_indents=1)

    test.pprint('Unit Tests Complete.', num_indents=0)
class StratUnitTests:

    def __init__(self):

        self.logfile_path = UNITTEST_LOGFILE_PATH
 
    def pprint(self, string='',
        num_indents=0,
        new_line_start=False,
        new_line_end=False):

        def output(out_loc):
            indent = len(INDENT)*' ' if out_loc != sys.stdout else INDENT
            total_indent0 = ''.join([indent] * num_indents)
            total_indent1 = ''.join([indent] * (num_indents + 1))
            if new_line_start:
                print(total_indent1 if DRAW_LINE else total_indent0, file=out_loc)
            for s in string.split('\n'):
                print(total_indent0 + s, file=out_loc)
            if new_line_end:
                print(total_indent1 if DRAW_LINE else total_indent0, file=out_loc)

        if OUTPUT_TO_CONSOLE:
            output(sys.stdout)
        if OUTPUT_TO_LOGFILE:
            logfile = open(self.logfile_path, 'a')
            output(logfile)
            logfile.close()

    def test_enter_long_market_order(self,
        verbose=False,
        num_indents=0):

        self.pprint('Test enter_long_market_order()', num_indents=num_indents)


        # percent = False

        # test sufficient funds
        if verbose: self.pprint('test sufficient funds,     percent=False', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_long_market_order(
            'exchange',
            1.5,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        assert(order_id == None and status == 'Trade Successful.')
        strat.update(verbose=verbose, num_indents=num_indents+2)
        assert(strat.portfolio['exchange'][COIN2][-1] == 1.5)
        if verbose: self.pprint('test successful.', num_indents=num_indents+1)

        # test insufficient funds
        if verbose: self.pprint('test insufficient funds,   percent=False', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_long_market_order(
            'exchange',
            1000.0,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        assert(order_id == None and status == 'Could not afford trade.')
        if verbose: self.pprint('test successful.', num_indents=num_indents+1)



        # percent = True

        if verbose: self.pprint('test sufficient funds,     percent=True', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_long_market_order(
            'exchange',
            0.50,
            percent=True,
            verbose=verbose,
            num_indents=num_indents+2)
        assert(order_id == None and status == 'Trade Successful.')
        strat.update(verbose=verbose, num_indents=num_indents+2)
        assert(strat.portfolio['exchange'][COIN1][-1] == 25000)
        if verbose: self.pprint('test successful.', num_indents=num_indents+1)

        # test insufficient funds
        if verbose: self.pprint('test insufficient funds,   percent=True', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_long_market_order(
            'exchange',
            2.00,
            percent=True,
            verbose=verbose,
            num_indents=num_indents+2)
        assert(order_id == None and status == 'Could not afford trade.')
        if verbose: self.pprint('test successful.', num_indents=num_indents+1)


        self.pprint('Test Successful.', num_indents=num_indents)
    def test_enter_short_market_order(self,
        verbose=False,
        num_indents=0):

        self.pprint('Test enter_short_market_order()', num_indents=num_indents)


        # percent = False

        # test sufficient funds
        if verbose: self.pprint('test sufficient funds,     percent=False', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_short_market_order(
            'margin',
            1.5,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        assert(order_id == None and status == 'Trade Successful.')
        strat.update(verbose=verbose, num_indents=num_indents+2)
        assert(strat.portfolio['margin'][COIN2][-1] == -1.5)
        if verbose: self.pprint('test successful.', num_indents=num_indents+1)

        # test insufficient funds
        if verbose: self.pprint('test insufficient funds,   percent=False', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_short_market_order(
            'margin',
            1000.0,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        assert(order_id == None and status == 'Could not afford trade.')
        if verbose: self.pprint('test successful.', num_indents=num_indents+1)



        # percent = True

        if verbose: self.pprint('test sufficient funds,     percent=True', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_short_market_order(
            'margin',
            0.50,
            percent=True,
            verbose=verbose,
            num_indents=num_indents+2)
        assert(order_id == None and status == 'Trade Successful.')
        strat.update(verbose=verbose, num_indents=num_indents+2)
        assert(strat.portfolio['margin'][COIN1][-1] == 50000)
        if verbose: self.pprint('test successful.', num_indents=num_indents+1)

        # test insufficient funds
        if verbose: self.pprint('test insufficient funds,   percent=True', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_short_market_order(
            'margin',
            2.00 * MAX_LEVERAGE, # 200% of max leverage
            percent=True,
            verbose=verbose,
            num_indents=num_indents+2)
        assert(order_id == None and status == 'Could not afford trade.')
        if verbose: self.pprint('test successful.', num_indents=num_indents+1)


        self.pprint('Test Successful.', num_indents=num_indents)
    
    def test_exit_long_market_order(self,
        verbose=False,
        num_indents=0):

        self.pprint('Test exit_long_market_order()', num_indents=num_indents)


        # percent = False

        # test sufficient funds
        if verbose: self.pprint('test sufficient funds,     percent=False', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_long_market_order( # enter 2.0 COIN2
            'exchange',
            2.0,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        order_id, status = strat.exit_long_market_order( # exit 10 COIN2
            'exchange',
            1.0,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        assert(order_id == None and status == 'Trade Successful.')
        strat.update(verbose=verbose, num_indents=num_indents+2)
        assert(strat.portfolio['exchange'][COIN2][-1] == 1.0)
        if verbose: self.pprint('test successful.', num_indents=num_indents+1)

        # test insufficient funds
        if verbose: self.pprint('test insufficient funds,   percent=False', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_long_market_order(
            'exchange',
            2.0,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        order_id, status = strat.exit_long_market_order(
            'exchange',
            3.0,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        assert(order_id == None and status == 'Could not afford trade.')
        if verbose: self.pprint('test successful.', num_indents=num_indents+1)



        # percent = True

        if verbose: self.pprint('test sufficient funds,     percent=True', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_long_market_order(
            'exchange',
            0.80,
            percent=True,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        order_id, status = strat.exit_long_market_order(
            'exchange',
            1.00,
            percent=True,
            verbose=verbose,
            num_indents=num_indents+2)
        assert(order_id == None and status == 'Trade Successful.')
        strat.update(verbose=verbose, num_indents=num_indents+2)
        assert(strat.portfolio['exchange'][COIN2][-1] == 0.0)
        if verbose: self.pprint('test successful.', num_indents=num_indents+1)

        # test insufficient funds
        if verbose: self.pprint('test insufficient funds,   percent=True', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_long_market_order(
            'exchange',
            0.80,
            percent=True,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        order_id, status = strat.exit_long_market_order(
            'exchange',
            1.10,
            percent=True,
            verbose=verbose,
            num_indents=num_indents+2)
        assert(order_id == None and status == 'Could not afford trade.')
        if verbose: self.pprint('test successful.', num_indents=num_indents+1)

        self.pprint('Test Successful.', num_indents=num_indents)
    def test_exit_short_market_order(self,
        verbose=False,
        num_indents=0):

        self.pprint('Test exit_short_market_order()', num_indents=num_indents)


        # percent = False

        # test sufficient funds
        if verbose: self.pprint('test sufficient funds,     percent=False', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_short_market_order( # enter 2.0 COIN2
            'margin',
            2.0,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        order_id, status = strat.exit_short_market_order( # exit 10 COIN2
            'margin',
            1.0,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        assert(order_id == None and status == 'Trade Successful.')
        strat.update(verbose=verbose, num_indents=num_indents+2)
        assert(strat.portfolio['margin'][COIN2][-1] == -1.0)
        if verbose: self.pprint('test successful.', num_indents=num_indents+1)

        # test insufficient funds
        if verbose: self.pprint('test insufficient funds,   percent=False', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_short_market_order(
            'margin',
            2.0,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        order_id, status = strat.exit_short_market_order(
            'margin',
            3.0,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        assert(order_id == None and status == 'Could not afford trade.')
        if verbose: self.pprint('test successful.', num_indents=num_indents+1)



        # # percent = True

        if verbose: self.pprint('test sufficient funds,     percent=True', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_short_market_order(
            'margin',
            0.80,
            percent=True,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        order_id, status = strat.exit_short_market_order(
            'margin',
            1.00,
            percent=True,
            verbose=verbose,
            num_indents=num_indents+2)
        assert(order_id == None and status == 'Trade Successful.')
        strat.update(verbose=verbose, num_indents=num_indents+2)
        assert(strat.portfolio['margin'][COIN2][-1] == 0.0)
        if verbose: self.pprint('test successful.', num_indents=num_indents+1)

        # test insufficient funds
        if verbose: self.pprint('test insufficient funds,   percent=True', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_short_market_order(
            'margin',
            0.80,
            percent=True,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        order_id, status = strat.exit_short_market_order(
            'margin',
            1.10,
            percent=True,
            verbose=verbose,
            num_indents=num_indents+2)
        assert(order_id == None and status == 'Could not afford trade.')
        if verbose: self.pprint('test successful.', num_indents=num_indents+1)

        self.pprint('Test Successful.', num_indents=num_indents)

    def test_enter_long_limit_order(self,
        verbose=False,
        num_indents=0):

        self.pprint('Test Enter Long Limit Order', num_indents=num_indents)

        if verbose: self.pprint('test limit_price is more than current price', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        current_price = strat.price
        order_id, trade_message = strat.enter_long_limit_order(
            'exchange',
            1.0,
            current_price * 1.10,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        assert(order_id == None and trade_message == 'Trade Successful.')
        if verbose: self.pprint('Test Successful.', num_indents=num_indents+1)

        if verbose: self.pprint('test limit_price is less than current price (an open order is created)', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        current_price = strat.price
        order_id, trade_message = strat.enter_long_limit_order(
            'exchange',
            1.0,
            current_price * 0.60,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        assert(order_id != None and len(strat.open_orders) == 1 and trade_message == 'Created enter long open limit order')
        if verbose: self.pprint('Test Successful.', num_indents=num_indents+1)

        self.pprint('Test Successful.', num_indents=num_indents)
    def test_enter_short_limit_order(self,
        verbose=False,
        num_indents=0):

        self.pprint('Test Enter Short Limit Order', num_indents=num_indents)

        if verbose: self.pprint('test limit_price is less than current price', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        current_price = strat.price
        order_id, trade_message = strat.enter_short_limit_order(
            'margin',
            1.0,
            current_price * 0.90,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        assert(order_id == None and trade_message == 'Trade Successful.')
        if verbose: self.pprint('Test Successful.', num_indents=num_indents+1)

        if verbose: self.pprint('test limit_price is more than current price (an open order is created)', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        current_price = strat.price
        order_id, trade_message = strat.enter_short_limit_order(
            'margin',
            1.0,
            current_price * 1.60,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        assert(order_id != None and len(strat.open_orders) == 1 and trade_message == 'Created enter short open limit order')
        if verbose: self.pprint('Test Successful.', num_indents=num_indents+1)

        self.pprint('Test Successful.', num_indents=num_indents)

    def test_exit_long_limit_order(self,
        verbose=False,
        num_indents=0):

        self.pprint('Test Exit Long Limit Order', num_indents=num_indents)

        if verbose: self.pprint('test limit_price is less than current price', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_long_market_order(
            'exchange',
            1.0,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        current_price = strat.price
        order_id, trade_message = strat.exit_long_limit_order(
            'exchange',
            1.0,
            current_price * 0.60,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        assert(order_id == None and trade_message == 'Trade Successful.')
        assert(strat.portfolio['exchange'][COIN2][-1] == 0)
        if verbose: self.pprint('Test Successful.', num_indents=num_indents+1)

        if verbose: self.pprint('test limit_price is more than current price (an open order is created)', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_long_market_order(
            'exchange',
            1.0,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        current_price = strat.price
        order_id, trade_message = strat.exit_long_limit_order(
            'exchange',
            1.0,
            current_price * 1.60,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        assert(order_id != None and len(strat.open_orders) == 1 and trade_message == 'Created exit long open limit order')
        if verbose: self.pprint('Test Successful.', num_indents=num_indents+1)

        self.pprint('Test Successful.', num_indents=num_indents)
    def test_exit_short_limit_order(self,
        verbose=False,
        num_indents=0):

        self.pprint('Test Exit Short Limit Order', num_indents=num_indents)

        if verbose: self.pprint('test limit_price is more than current price', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_short_market_order(
            'margin',
            1.0,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        current_price = strat.price
        order_id, trade_message = strat.exit_short_limit_order(
            'margin',
            1.0,
            current_price * 1.40,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        assert(order_id == None and trade_message == 'Trade Successful.')
        assert(strat.portfolio['exchange'][COIN2][-1] == 0)
        if verbose: self.pprint('Test Successful.', num_indents=num_indents+1)

        if verbose: self.pprint('test limit_price is less than current price (an open order is created)', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_short_market_order(
            'margin',
            1.0,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        current_price = strat.price
        order_id, trade_message = strat.exit_short_limit_order(
            'margin',
            1.0,
            current_price * 0.90,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        assert(order_id != None and len(strat.open_orders) == 1 and trade_message == 'Created exit short open limit order')
        if verbose: self.pprint('Test Successful.', num_indents=num_indents+1)

        self.pprint('Test Successful.', num_indents=num_indents)

    def test_convert_enter_to_exit_opposite(self,
        verbose=False,
        num_indents=0):

        self.pprint('Test Convert Enter to Exit', num_indents=num_indents)
        
        if verbose: self.pprint('test convert enter long to exit short opposite (new more than old)', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_short_market_order(
            'margin',
            1.0,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        order_id, status = strat.enter_long_market_order(
            'margin',
            1.5,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        assert(strat.portfolio['margin'][COIN2][-1] == 0.5)
        if verbose: self.pprint('test successful.', num_indents=num_indents+1)

        if verbose: self.pprint('test convert enter long to exit short opposite (new less than old)', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_short_market_order(
            'margin',
            1.0,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        order_id, status = strat.enter_long_market_order(
            'margin',
            0.5,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        assert(strat.portfolio['margin'][COIN2][-1] == -0.5)
        if verbose: self.pprint('test successful.', num_indents=num_indents+1)


        if verbose: self.pprint('test convert enter short to exit long opposite (new more than old)', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_long_market_order(
            'margin',
            1.0,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        order_id, status = strat.enter_short_market_order(
            'margin',
            1.5,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        assert(strat.portfolio['margin'][COIN2][-1] == -0.5)
        if verbose: self.pprint('test successful.', num_indents=num_indents+1)

        if verbose: self.pprint('test convert enter short to exit long opposite (new less than old)', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_long_market_order(
            'margin',
            1.0,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        order_id, status = strat.enter_short_market_order(
            'margin',
            0.5,
            percent=False,
            verbose=verbose,
            num_indents=num_indents+2)
        strat.update(verbose=verbose, num_indents=num_indents+2)
        assert(strat.portfolio['margin'][COIN2][-1] == 0.5)
        if verbose: self.pprint('test successful.', num_indents=num_indents+1)

        self.pprint('Test Successful.', num_indents=num_indents)

    def test_leverage(self,
        verbose=False,
        num_indents=0):

        self.pprint('Test Leverage', num_indents=num_indents)

        if verbose: self.pprint('test enter more than collateral but less than MAX_LEVERAGE', num_indents=num_indents+1)
        strat = Strat(
            backtesting=True,
            verbose=verbose,
            num_indents=num_indents+2,
            logfile_path=self.logfile_path,
            clear_log=False)
        order_id, status = strat.enter_long_market_order(
            'margin',
            1.50,
            percent=True,
            verbose=verbose,
            num_indents=num_indents+2)
        assert(order_id == None and status == 'Trade Successful.')
        strat.update(verbose=verbose, num_indents=num_indents+2)
        assert(strat.portfolio['margin'][COIN1][-1] == 75000)
        if verbose: self.pprint('test successful.', num_indents=num_indents+1)



        # test enter more than MAX_LEVERAGE

        self.pprint('Test Successful.', num_indents=num_indents)

    def test_forced_liquidation(self,
        verbose=False,
        num_indents=0):

        self.pprint('Test Forced Liquidation', num_indents=num_indents)
        
        # tbd

        self.pprint('Test Successful.', num_indents=num_indents)

    def test_trading_fee(self,
        verbose=False,
        num_indents=0):

        self.pprint('Test Trading Fee', num_indents=num_indents)
        
        # tbd

        # sell all of exchange portfolio into COIN2
        # there should be x COIN2s worth of the original value * (1 - trading_fee) in COIN2

        self.pprint('Test Successful.', num_indents=num_indents)


if __name__ == '__main__':

    # run_unittests(verbose=True)

    strat = Strat()
    strat.backtest()

