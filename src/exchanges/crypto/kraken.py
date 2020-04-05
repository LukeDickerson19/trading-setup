import sys
import os
import subprocess
import requests
import json
import time
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
import pathlib
SCRIPT_PATH         = pathlib.Path(__file__).resolve()
ROOT_PATH           = SCRIPT_PATH.parent.parent.parent.parent
SRC_PATH            = os.path.join(ROOT_PATH.absolute(), 'src')
API_KEY_PATH        = os.path.join(SRC_PATH, 'api_keys.json')
DATA_PATH           = os.path.join(ROOT_PATH.absolute(), 'data', 'crypto', 'kraken')
ORDERBOOK_DATA_PATH = os.path.join(DATA_PATH, 'order_book')
sys.path.append(SRC_PATH)
sys.path.append(DATA_PATH)
sys.path.append(ORDERBOOK_DATA_PATH)
# print('SCRIPT_PATH        ', SCRIPT_PATH.absolute())
# print('ROOT_PATH          ', ROOT_PATH.absolute())
# print('SRC_PATH           ', SRC_PATH)
# print('API_KEY_PATH       ', API_KEY_PATH)
# print('DATA_PATH          ', DATA_PATH)
# print('ORDERBOOK_DATA_PATH', ORDERBOOK_DATA_PATH)



class Kraken:

	def __init__(self, account_name='account1'):
		info = json.load(open(API_KEY_PATH, 'r'))
		self.api_key      = info['exchanges']['kraken'][account_name]['api_key']
		self.private_key  = info['exchanges']['kraken'][account_name]['private_key']
		self.base_url     = 'https://api.kraken.com/0'
		self.account_name = account_name

	''' get_current_price
		Returns:
			current_price - float - price of most recent trade of currency_pair
		Arguments:
			currency_pair - string - format: 'X'+coin1+'Z'+coin2, ex: 'XXBTZUSD'			
		'''
	def get_current_price(self, currency_pair):
		most_recent_trade = self.get_recent_trades(currency_pair)[0]
		return float(most_recent_trade[0])

	''' get_recent_trades
		Returns:
			[[<price>, <volume>, <time>, <buy/sell>, <market/limit>, <miscellaneous>], ...]
			sorted from most recent to least recent
		Arguments:
			currency_pair - string - format: 'X'+coin1+'Z'+coin2, ex: 'XXBTZUSD'
		'''
	def get_recent_trades(self, currency_pair):
		url = self.base_url + '/public/Trades'
		data = {
			'pair' : currency_pair,
		}
		response = requests.post(url, params=data)
		recent_trades = json.loads(response.text)['result'][currency_pair]

		# sorted from most recent to least recent
		recent_trades = sorted(recent_trades, key=lambda trade : trade[2], reverse=True)
		return recent_trades

	''' get_current_order_book
		Returns:
			{
				"asks" : [[<price>, <volume>, <unix_timestamp>], ...],
				"bids" : [[<price>, <volume>, <unix_timestamp>], ...]
			}
		Arguments:
			currency_pair - string - format: 'X'+coin1+'Z'+coin2, ex: 'XXBTZUSD'
			count - int - max number of orders to return
			save_filename - string - json filepath to append orderbook too, leave as None if you don't want to save it
		'''
	def get_current_order_book(self, currency_pair, count=100000):
		url = self.base_url + '/public/Depth'
		data = {
			'pair' : currency_pair
		}
		if count != None:
			data['count'] = count
		response = requests.post(url, params=data)
		order_book = json.loads(response.text)['result'][currency_pair]
		return order_book

	''' get_orderbook_and_recent_trades
		Returns:
			{
				'order_book' : {
					"asks" : [[<price>, <volume>, <unix_timestamp>], ...],
					"bids" : [[<price>, <volume>, <unix_timestamp>], ...]
				},
				'recent_trades' : {
					"start_time" : unix_timestamp,
					"end_time" : unix_timestamp,
					"trades" : [[<price>, <volume>, <time>, <buy/sell>, <market/limit>, <miscellaneous>], ...]
									sorted from most recent to least recent
				}
			}
		Arguments:
			currency_pair - string - format: 'X'+coin1+'Z'+coin2, ex: 'XXBTZUSD'
			start_time_dt - datetime object - get all trades that occured between start_time_dt and now
				if the API fails 
		'''
	def get_orderbook_and_recent_trades(self, currency_pair, start_minutes_timedelta, filename):

		# get orderbook and recent trades data
		now = datetime.now(timezone.utc)
		start_time_dt = now - timedelta(minutes=start_minutes_timedelta)
		start_time_unix = start_time_dt.timestamp()
		recent_trades = self.get_recent_trades(currency_pair)
		order_book = self.get_current_order_book(currency_pair)
		order_book['asks'] = [[float(ask[0]), float(ask[1]), int(ask[2])] for ask in order_book['asks']]
		order_book['bids'] = [[float(bid[0]), float(bid[1]), int(bid[2])] for bid in order_book['bids']]
		recent_trades = [t for t in recent_trades if start_time_unix <= t[2]] # filter out trades before start time
		recent_trades = [[float(t[0]), float(t[1]), float(t[2]), t[3], t[4]] for t in recent_trades] # filter out miscellaneous data and convert numeric data from string to float
		ret = {
			'order_book'     : order_book,
			'recent_trades'  : {
				'start_time' : start_time_dt.strftime('%Y/%m/%d %H:%M:%S %z'),
				'trades'     : recent_trades
			},
			'current_price'  : recent_trades[0][0]
		}

		# save data to filename
		filepath = os.path.join(ORDERBOOK_DATA_PATH, filename)
		try:
			f = open(filepath, 'r')
		except FileNotFoundError:
			f = open(filepath, 'w+')
			json.dump({}, f, indent=4)
			f.close()
		j = json.load(open(filepath, 'r'))
		j[now.strftime('%Y/%m/%d %H:%M:%S %z')] = ret
		json.dump(j, open(filepath, 'w'), indent=4)

		# return data
		return ret

	''' get_price_history
		Returns:
			list of OHLC data. Format: [(open, high, low, close, volume_weighted_average_price, volume), ...]
		Arguments:
			currency_pair - string - format: 'X'+coin1+'Z'+coin2, ex: 'XXBTZUSD'
			start_time_dt - datetime - end time of data
			end_time_dt - datetime - end time of data
			interval - int? - time frame interval in minutes.
				valid values:
					1     - 1 min (default)
					5     - 5 min
					15    - 15 min
					30    - 30 min
					60    - 1 hr
					240   - 4 hrs
					1440  - 1 day
					10080 - 1 week
					21600 - 2week (15 days actually)
			verbose - boolean - whether to price the return value to the console or not
		'''
	def get_price_history(self, currency_pair, start_time_dt, end_time_dt, interval, verbose=False):
		
		# get the data from the kraken API, and parse the information you actually want
		# source: https://www.kraken.com/en-us/features/api#get-ohlc-data
		# raw format: [[<time>, <open>, <high>, <low>, <close>, <vwap>, <volume>, <count>], ...]
		url = self.base_url + '/public/OHLC'
		data = {
			'pair'     : currency_pair,
			'interval' : interval,
			'since'    : start_time_dt.timestamp()
		}
		response = requests.post(url, params=data)
		price_data = json.loads(response.text)['result'][currency_pair]
		price_data = {data[0] : list(map(lambda p : float(p), data[1:])) for data in price_data}

		# kraken's get OHLC API call gets data from start_time to present
		# so clip off the data after end_time
		price_data = dict(filter(lambda kv_tuple : kv_tuple[0] <= end_time_dt.timestamp(), price_data.items()))		

		if verbose:
			for k, v in price_data.items():
				print(k, v)

		return price_data

	''' get_percent_change_history
		Returns:
			list of percent change from previous price. Format: [(percent_change, volume_weighted_average_price, volume), ...]
		Arguments:
			currency_pair - string - format: 'X'+coin1+'Z'+coin2, ex: 'XXBTZUSD'
			start_time_dt - datetime - end time of data
			end_time_dt - datetime - end time of data
			interval - int? - time frame interval in minutes.
				valid values:
					1     - 1 min (default)
					5     - 5 min
					15    - 15 min
					30    - 30 min
					60    - 1 hr
					240   - 4 hrs
					1440  - 1 day
					10080 - 1 week
					21600 - 2week (15 days actually)
			verbose - boolean - whether to price the return value to the console or not
		'''
	def get_percent_change_history(self, currency_pair, start_time_dt, end_time_dt, interval, verbose=False):

		# get price data
		price_data = self.get_price_history(currency_pair, start_time_dt, end_time_dt, interval)

		# get percent change of each price from the previous price
		# clip the first price with no previous price to calculate percent change
		percent_change_data = {}
		prev_price = None
		for ut, data in price_data.items():
			price = data[4] # use: volume_weighted_average_price
			if prev_price == None:
				prev_price = price
				continue
			percent_change_data[ut] = (100.0 * (price - prev_price) / prev_price, price)
			prev_price = price

		if verbose:
			for ut, pct_chng in percent_change_data.items():
				print(ut, '\t', pct_chng)

		return percent_change_data

	''' get_price_windows
		Returns:
			dictionary
				key - int - unixtime
				value - list of floats - list of prices in window at the given unixtime, price at index 0 is the most recent
		Arguments:
			price_data - see return of get_price_history
			windows - list of ints - time window frames to return
			verbose - boolean - whether to price the return value to the console or not
		'''
	def get_price_windows(self, price_data, windows, verbose=False):
		prc_dta = [[dt, data[4]] for dt, data in price_data.items()] # use data[4]: volume_weighted_average_price
		price_windows = {w : \
			{prc_dta[i-1][0] : \
				list(map(lambda e : e[1], prc_dta[i-w:i])) \
				for i in range(w, len(prc_dta)+1)}
					for w in windows}
		if verbose:
			for w in windows:
				print(w)
				input()
				for k, v in price_windows[w].items():
					print(k, v)
				input()
		return price_windows

	''' get_percent_change_windows
		Returns:
			dictionary
				key - int - unixtime
				value - list of floats - list of percentage changes in window at the given unixtime, price at index 0 is the most recent
		Arguments:
			percent_change_data - see return of get_percent_change_history
			windows - list of ints - time window frames to return
			verbose - boolean - whether to price the return value to the console or not
		'''
	def get_percent_change_windows(self, percent_change_data, window, verbose=False):
		pct_chng_dta = [[dt, data[0]] for dt, data in percent_change_data.items()]
		percent_change_windows = {w : \
			{pct_chng_dta[i-1][0] : \
				list(map(lambda e : e[1], pct_chng_dta[i-w:i])) \
				for i in range(w, len(pct_chng_dta)+1)}
					for w in windows}
		if verbose:
			for w in windows:
				print(w)
				input()
				for k, v in percent_change_windows[w].items():
					print(k, v)
				input()
		return percent_change_windows

	''' indicator_historic
		Returns:
			dicitonary
				key - int - unixtime
				value - float - current value of indicator
		Arguments:
			data_windows - see return of get_price_windows or get_percent_change_windows
			indicator_function - indicator function that takes price_w (list of floats of price window) wrapped in a lambda function
								 see example in main function
			verbose - boolean - whether to price the return value to the console or not
		'''
	def indicator_historic(self, data_windows, indicator_function, verbose=False):
		indicator_historic = {}
		for w, data_ws in data_windows.items():
			indicator_historic[w] = {}
			for ut, data_w in data_ws.items():
				indicator_historic[w][ut] = indicator_function(data_w)
		if verbose:
			for w, data_ws in data_windows.items():
				print('window', w)
				input()
				for ut, _ in data_ws.items():
					print(ut, '\t', indicator_historic[w][ut])
				input()
		return indicator_historic

	''' stochastic_oscillator
		Returns:
			float - stockastic oscillator of price_w
					how to calculate it: https://www.investopedia.com/terms/s/stochasticoscillator.asp
		Arguments:
			price_w - list of floats - price window
			verbose - boolean - whether to price the return value to the console or not
		'''
	def stochastic_oscillator(self, price_w, verbose=False):

		return 100 * (price_w[0] - min(price_w)) / (max(price_w) - min(price_w))

	''' relative_strength_index
		Returns:
			float - relative strength index of pct_chng_W
					how to calculate it:
						1. https://www.investopedia.com/terms/r/rsi.asp
						2. https://en.wikipedia.org/wiki/Relative_strength_index
						3. https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/RSI
					theres conflicting examples on how to calculate it, i went with link 3.
		Arguments:
			pct_chng_w - list of floats - percent change window
			verbose - boolean - whether to price the return value to the console or not
		'''
	def relative_strength_index(self, pct_chng_w, verbose=False):
		
		average_gain = np.array(list(filter(lambda pct_chng : pct_chng > 0.0, pct_chng_w))).mean()
		average_loss = np.array(list(filter(lambda pct_chng : pct_chng < 0.0, pct_chng_w))).mean()

		# average_gain = np.array(list(filter(lambda pct_chng : pct_chng > 0.0, pct_chng_w[1:]))).mean()
		# average_loss = np.array(list(filter(lambda pct_chng : pct_chng < 0.0, pct_chng_w[1:]))).mean()
		# average_gain = 1.0 * pct_chng[0] + (len(pct_chng_w) - 1) * average_gain
		# average_loss = 1.0 * pct_chng[0] + (len(pct_chng_w) - 1) * average_loss

		rs = average_gain / abs(average_loss)
		rsi1 = 100.0 - (100.0 / (1.0 + rs))
		rsi2 = None
		return rsi1





if __name__ == '__main__':

	kraken = Kraken()

	coin1, coin2 = 'XBT', 'USD'
	currency_pair = 'X' + coin1 + 'Z' + coin2 # ex: 'XXBTZEUR'
	filename = '%s_%s_order_books_and_trades.json' % (coin1, coin2)

	# # test get_orderbook_and_recent_trades
	# start_minutes_timedelta = 5
	# ret = kraken.get_orderbook_and_recent_trades(
	# 		currency_pair,
	# 		start_minutes_timedelta,
	# 		filename)
	# json.dump(ret, sys.stdout, indent=4)


	# test get_price_history() and get_percent_change_history()
	start_time_dt = datetime(2019, 8, 1, tzinfo=timezone.utc) # datetime(year, month, day, hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
	end_time_dt   = datetime(2020, 3, 1, tzinfo=timezone.utc) # datetime(year, month, day, hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
	interval = 1440 # 1 day
	price_data = kraken.get_price_history(
		currency_pair,
		start_time_dt,
		end_time_dt,
		interval,
		verbose=False)
	percent_change_data = kraken.get_percent_change_history(
		currency_pair,
		start_time_dt,
		end_time_dt,
		interval,
		verbose=False)

	# test get_price_windows() and get_percent_change_windows()
	windows = [10, 100]
	price_windows = kraken.get_price_windows(
		price_data, windows)
	percent_change_windows = kraken.get_percent_change_windows(
		percent_change_data, windows, verbose=False)

	# test stochastic_oscillator
	so = kraken.indicator_historic(
		price_windows,
		lambda price_w : kraken.stochastic_oscillator(price_w),
		verbose=False)

	# test relative_strength_index()
	rsi = kraken.indicator_historic(
		percent_change_windows,
		lambda pct_chng_w : kraken.relative_strength_index(pct_chng_w),
		verbose=True)
