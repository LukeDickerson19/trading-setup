import sys
import os
import subprocess
import requests
import json
import time
from datetime import datetime, timezone
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
print('SCRIPT_PATH        ', SCRIPT_PATH.absolute())
print('ROOT_PATH          ', ROOT_PATH.absolute())
print('SRC_PATH           ', SRC_PATH)
print('API_KEY_PATH       ', API_KEY_PATH)
print('DATA_PATH          ', DATA_PATH)
print('ORDERBOOK_DATA_PATH', ORDERBOOK_DATA_PATH)



class Kraken:

	def __init__(self, account_name='account1'):
		info = json.load(open(API_KEY_PATH, 'r'))
		self.api_key      = info['exchanges']['kraken'][account_name]['api_key']
		self.private_key  = info['exchanges']['kraken'][account_name]['private_key']
		self.base_url     = 'https://api.kraken.com/0'
		self.account_name = account_name


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
	def get_current_order_book(self, currency_pair, count=None, save_filename=None):
		url = self.base_url + '/public/Depth'
		data = {
			'pair' : currency_pair,
		}
		if count != None:
			data['count'] = count
		response = requests.post(url, params=data)
		order_book = json.loads(response.text)['result'][currency_pair]
		if save_filename:
			filepath = os.path.join(ORDERBOOK_DATA_PATH, save_filename)
			try:
				f = open(filepath, 'r')
			except FileNotFoundError:
				f = open(filepath, 'w+')
				j = {'data': {}}
				json.dump(j, f, indent=4)
				f.close()

			j = json.load(open(filepath, 'r'))
			print(datetime.now(timezone.utc).tzinfo)
			now = datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M:%S %z")
			j['data'][now] = order_book
			json.dump(j, open(filepath, 'w'), indent=4)
		return order_book



if __name__ == '__main__':

	kraken = Kraken()

	coin1, coin2 = 'XBT', 'USD'
	currency_pair = 'X' + coin1 + 'Z' + coin2 # ex: 'XXBTZEUR'
	filename = '%s_%s_order_books.json' % (coin1, coin2)
	print(kraken.get_current_order_book(currency_pair, save_filename=filename))
