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
DATA_PATH           = os.path.join(ROOT_PATH.absolute(), 'data', 'stocks', 'alpaca')
API_KEYS            = json.load(open(API_KEY_PATH, 'r'))
sys.path.append(SRC_PATH)
sys.path.append(DATA_PATH)
# print('SCRIPT_PATH        ', SCRIPT_PATH.absolute())
# print('ROOT_PATH          ', ROOT_PATH.absolute())
# print('SRC_PATH           ', SRC_PATH)
# print('API_KEY_PATH       ', API_KEY_PATH)
# print('DATA_PATH          ', DATA_PATH)



class Alpaca:

	def __init__(self, account_name='', paper_trading=True, verbose=True):

		''' Account Example:
			{
				"email"      : "",
				"password"   : "",
				"2FA"        : "",
				"paper_trading" : {
					"ENDPOINT"       : ""
					"API_KEY_ID"     : ""
					"SECRET_KEY"     : ""
				},
				"live_trading"  : {
					"ENDPOINT"       : ""
					"API_KEY_ID"     : ""
					"SECRET_KEY"     : ""
				}
			}
				'''
		if account_name not in list(API_KEYS['exchanges']['alpaca'].keys()):
			print('Invalid account name given to constructor of Alpaca class.')
			print('Account name: \"%s\"' % account_name)
			sys.exit()
		self.account = API_KEYS['exchanges']['alpaca'][account_name]
		self.api_keys = self.account['paper_trading' if paper_trading else 'live_trading']

		self.account_url = '{}/v2/account'.format(self.api_keys['ENDPOINT'])
		r = requests.get(
			self.account_url,
			headers={
				'APCA-API-KEY-ID'     : self.api_keys['API_KEY_ID'],
				'APCA-API-SECRET-KEY' : self.api_keys['SECRET_KEY']
			})
		if verbose:
			print(json.dumps(self.api_keys, indent=4))
			print(r.content)

	''' get_fundamental_data:

		RETRUNS:
			fundamental_data: dictionary of fundamental data for the asset tickers in asset_list:
				key=ticker
				value=pandas df with folling columns
					col1
					col2
					col3

		ARGUMENTS:
			asset_list:    list of strings - list of ticker symbols of the assets we want data on
			start_time_dt: datetime        - time to start getting fundamental data
			end_time_dt:   datetime        - time to end getting fundamental data
			period:        int             - duration of time between samples. Optional Argument, default_value: 'quarterly', valid_values: ['quarterly'] 
			save:          boolean         - wether or not to save the data to a CSV file
			overwrite:     boolean         - wether or not to overwrite a pre existing file with the same name
		'''
	def get_fundamental_data(self, asset_list, start_time_dt, end_time_dt, period='quarterly', save=False, overwrite=False):
		pass

	def get_current_price(self, asset_list):
		pass

	def get_price_history(self, asset_list, start_time_dt, end_time_dt, period='daily', verbose=True):
		if verbose:
			print('Getting price history for %d asset%s:' % (len(asset_list), '' if len(asset_list) == 1 else 's'))
			for i, asset in enumerate(asset_list):
				print(i+1, '\t', asset)
			print('start_time_dt = %s' % start_time_dt)
			print('end_time_dt   = %s' % end_time_dt)
			print('period        = %s' % period)

		''' Valid Periods:

			'''



	def limit_order(self, asset, num_shares, limit_price):
		pass



if __name__ == '__main__':

	alpaca = Alpaca(account_name='account1', paper_trading=False)

	# ticker = 'AAPL'
	# start_time_dt = datetime(2020, 1, 1,  0, 0, 0)
	# end_time_dt   = datetime(2020, 1, 14, 0, 0, 0)
	# period = 'daily'
	# alpaca.get_price_history([ticker], start_time_dt, end_time_dt, period)

