import sys
import os
import pathlib
SCRIPT_PATH   = pathlib.Path(__file__).resolve()
ROOT_PATH     = SCRIPT_PATH.parent.parent
LOG_PATH      = os.path.join(ROOT_PATH.absolute(), 'logs', 'backtest_log.txt')
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
        
        implement basic strat
        
    DESCRIPTION

        basic algo trading strategy setup for backtesting and live trading
        this just has enter() and exit() functions
        it takes the percentage change minus TF to get PL
        super simple, unrealistic but close enough

    SOURCES

        https://docs.bokeh.org/en/latest/docs/user_guide/layout.html

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
LOGFILE_PATH = None # set by Strat class or StratUnitTests class
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

        if verbose: self.pprint('Strategy Initialized.', num_indents=num_indents)
    
    # create strategy setup
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

        # select which account to use, options:
        # 'account1' aka lucius.dickerson@gmail.com
        # 'account2' aka private.mail285@gmail.com
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
    def backtest(self,
        num_periods='all',
        plot=False,
        verbose=False,
        num_indents=0):

        self.setup_backtesting(verbose=verbose, num_indents=num_indents+1)

        if num_periods == 'all':
            num_periods = self.num_periods

        # iterate over each timestep starting at t
        self.pprint('Iterating Over price data.', num_indents=num_indents)
        while self.t < num_periods:
            self.t += 1
            self.update(verbose=verbose, num_indents=num_indents+1)
        self.pprint('Backtest Complete.', num_indents=num_indents)

        if plot:
            self.plot(verbose=verbose, num_indents=num_indents)
    def setup_backtesting(self,
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

        df['exit_pl'] = np.nan # the P/L of an investment at time of exit (percent change of investment after fees)
        df['tot_pl'] = np.nan # the total P/L of the strategy (percentage change of strategy)
        df.at[t, 'tot_pl'] = 0
        self.open_positions = {}
        self.pl_update = 0

        self.df = df
        self.t = t
        self.start_t = t
        self.unix_date, self.date, self.price, self.pct_chg = df.iloc[t][:4]
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
            self.pprint('Backtesting Initialized.', num_indents=num_indents)
    def update(self,
        verbose=False, num_indents=0):

        self.unix_date, self.date, self.price, self.pct_chg, = self.df.iloc[self.t][:4]
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


        ########################################################## STRATEGY UPDATE GOES HERE ###################################################

        # tbd
        if t == 9:

            pos_id = self.enter('short', 10)

        elif t == 22:

            pos_id = self.exit(list(self.open_positions.keys())[0])

        ########################################################################################################################################

        # update profit/loss
        self.df.at[t, 'exit_pl'] = self.pl_update
        self.df.at[t, 'tot_pl']  = self.df.at[t-1, 'tot_pl'] + self.pl_update
        self.pl_update = 0

        self.pprint('Update Complete.', num_indents=num_indents)
        # input()

    # place order
    def enter(self,
        long_or_short,
        quantity,
        verbose=False,
        num_indents=0):

        position_id = self.get_position_id()
        self.open_positions[position_id] = {
            'long_or_short' : long_or_short,
            'enter_price'   : self.price,
            'enter_value'   : quantity
        }
        return position_id
    def exit(self,
        position_id,
        verbose=False,
        num_indents=0):

        enter_price = self.open_positions[position_id]['enter_price']
        exit_price  = self.price
        tf = TF if INCLUDE_TF else 0
        pl =  ((exit_price - enter_price) / enter_price) * (1 - tf)
        pl *= 1 if self.open_positions[position_id]['long_or_short'] == 'long' else -1
        pl *= self.open_positions[position_id]['enter_value']
        self.pl_update += pl

        del self.open_positions[position_id]
    def get_position_id(self):
        i = 0
        for pos_id in self.open_positions.keys():
            if pos_id > i:
                return i
            else:
                i += 1
        return i

    def plot(self,
        verbose=False,
        num_indents=0):

        fig, axes = plt.subplots(
            nrows=3, ncols=1,
            num='Figure Title',
            figsize=(10.75, 6.5),
            sharex=True, sharey=False)
        mng = plt.get_current_fig_manager()
        mng.resize(*mng.window.maxsize()) # go fullscreen
        _legend_loc, _b2a = 'center left', (1, 0.5) # puts legend ouside plot

        axes[0].plot(self.df[COIN2], color='black', label='Price')
        axes[0].grid()
        axes[0].set_xlim(left=0, right=self.df.shape[0]) # allign axes[0] other axes

        ''' Notes:
            cur_sl_pl was used instead of cur_price_pl because the sl will be triggered
            before the price reaches a value lower/higher than the stop loss
            '''
        def plot_vertical_lines(ax, pd_series, color, label):
            for i, val in pd_series.items():
                if not np.isnan(val):
                    ax.plot(
                        [i, i],
                        [0.0, 100 * val],
                        color=color)
        plot_vertical_lines(axes[1], self.df['exit_pl'],  'black', 'Exit P/L')
        # axes[1].legend(loc=_legend_loc, bbox_to_anchor=_b2a)
        axes[1].grid()
        axes[1].set_xlim(left=0, right=self.df.shape[0]) # allign axes[1] other axes

        # axes[1].yaxis.grid()  # draw horizontal lines
        # axes[1].yaxis.set_zorder(-1.0)  # draw horizontal lines behind histogram bars
        # axes[1].set_title('Current Profit/Loss', loc='Center')
        axes[1].set_ylabel('Percent Change')
        # axes[1].set_xticks(x_tick_indeces)
        # axes[1].set_xticklabels('')
        # axes[1].yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=1))

        axes[2].plot(100 * self.df['tot_pl'], color='black', label='Total P/L')
        # axes[2].plot(short_df['tot_price_pl'],    color='red',   label='Total Short Stop Loss P/L')
        # axes[2].plot(tsl_x_dct['tot_returns'],    color='blue',  label='Total Combined Stop Loss P/L')
        # axes[2].plot()
        # axes[2].legend(loc=_legend_loc, bbox_to_anchor=_b2a)
        # axes[2].grid()
        # # axes[2].yaxis.grid()  # draw horizontal lines
        # axes[2].yaxis.set_zorder(-1.0)  # draw horizontal lines behind histogram bars
        # axes[2].set_title('Total Profit/Loss')
        # axes[2].set_xticks(x_tick_indeces)
        # axes[2].set_xticklabels(date_labels, ha='right', rotation=45)  # x axis should show date_labeles
        # axes[2].yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=1))
        axes[2].set_ylabel('Percent Change')
        axes[2].grid()
        axes[2].set_xlim(left=0, right=self.df.shape[0]) # allign axes[0] other axes

        df_len = self.df.shape[0]
        timespan_label_ticks  = [0, int(1*df_len/4), int(2*df_len/4), int(3*df_len/4), df_len-1]
        timespan_ticks        = np.array([np.linspace(timespan_label_ticks[i-1], timespan_label_ticks[i], 10, dtype=int).tolist()[:-1] for i in range(1, len(timespan_label_ticks))]).flatten().tolist() + [df_len - 1]
        timespan_labels       = [self.df['datetime'].iloc[i][:10] if i in timespan_label_ticks else '' for i in timespan_ticks]
        axes[2].set_xticks(timespan_ticks)
        axes[2].set_xticklabels(timespan_labels, rotation=90)

        # plt.tight_layout()
        fig.subplots_adjust(
            right=0.95,
            left=0.075,
            bottom=0.15,
            top=0.95) # <-- Change the 0.02 to work for your plot.

        plt.show()


if __name__ == '__main__':

    strat = Strat(verbose=True)
    print(strat.logfile_path)
    strat.backtest(num_periods=100, verbose=True)

    strat.plot()
