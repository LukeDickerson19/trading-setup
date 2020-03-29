from config import *



class Alpaca:

	def __init__(self, account_name=''):

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
		# print(json.dumps(self.account, indent=4))

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



if __name__ == '__main__':

	alpaca = Alpaca(account_name='account1')