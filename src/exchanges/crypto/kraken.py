import sys
import os
import subprocess
import requests
import json
import time
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
			'pair' : currency_pair
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

	''' scrap_orderbook_and_recent_trades
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
	def scrap_orderbook_and_recent_trades(self, currency_pair, start_minutes_timedelta, filename):

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


if __name__ == '__main__':

	kraken = Kraken()

	coin1, coin2 = 'XBT', 'USD'
	currency_pair = 'X' + coin1 + 'Z' + coin2 # ex: 'XXBTZEUR'
	filename = '%s_%s_order_books_and_trades.json' % (coin1, coin2)
	start_minutes_timedelta = 5
	ret = kraken.scrap_orderbook_and_recent_trades(
		currency_pair, start_minutes_timedelta, filename)
	json.dump(ret, sys.stdout, indent=4)


