import sys
import os
import time
import json
import subprocess
import requests
from io import StringIO
from datetime import datetime
import numpy as np
import pandas as pd
MAX_ROWS = 50
pd.set_option('display.max_rows', MAX_ROWS)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 200)
import simfin as sf
from bs4 import BeautifulSoup as bs
import pathlib
SCRIPT_PATH    = pathlib.Path(__file__).resolve()
ROOT_PATH      = SCRIPT_PATH.parent.parent.parent.parent
RAW_DATA_PATH  = os.path.join(ROOT_PATH.absolute(), 'data', 'stocks', 'simfin', 'quarterly_fundamental_data', 'raw')
FMTD_DATA_PATH = os.path.join(ROOT_PATH.absolute(), 'data', 'stocks', 'simfin', 'quarterly_fundamental_data', 'formatted')
SRC_PATH       = os.path.join(ROOT_PATH.absolute(), 'src')
PLOT_DATA_PATH = os.path.join(ROOT_PATH.absolute(), 'data', 'stocks', 'simfin', 'pre_processed_plot_data.json')
sys.path.append(SRC_PATH)
# print(SCRIPT_PATH.absolute())
# print(ROOT_PATH.absolute())
# print(DATA_PATH)
# print(SRC_PATH)
# print(PLOT_DATA_PATH)
# sys.exit()
from block_printer import BlockPrinter
from collections import OrderedDict
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from mpl_toolkits.axes_grid1 import make_axes_locatable



class SimFinScrapper:

	def __init__(self):

		# Set your API-key for downloading data.
		# If the API-key is 'free' then you will get the free data,
		# otherwise you will get the data you have paid for.
		# See www.simfin.com for what data is free and how to buy more.
		sf.set_api_key('free')

		# Set the local directory where data-files are stored.
		# The dir will be created if it does not already exist.
		sf.set_data_dir(RAW_DATA_PATH)

		self.report_name = 'SimFin Data Coverage Report'



	''' get_data_of_all_assets
		Returns:
			assets: dictionary
				keys = ticker symbol
				values = pandas dataframe with fundamental data
							each row is a quarter
							columns:
								Quarter end
								Shares
								Shares split adjusted
								Split factor
								Assets
								Current Assets
								Liabilities
								Current Liabilities
								etc ...
									see NOTES.txt for full list and definitions
		Arguments:
			source:	string - string specifying where to get the data: valid_values: ['web', 'local']
			verbose - boolean - print to the console if True
		'''
	def get_data_of_all_assets(self, source, verbose=True):

		if source == 'web':

			# verify the website has the same number of assets as local (or local has 0)
			if verbose:
				print('\nVerifying the website has the same number of assets as local (or local has 0) ...')
			assets_on_web   = self.get_all_asset_names_and_locations('web')
			assets_on_local = self.get_all_asset_names_and_locations('local')
			if len(set(assets_on_local)) == 0:
				pass # this IF block is used to check if local has 0 before checking if their equal
			elif len(set(assets_on_web)) != len(set(assets_on_local)):
				print('Number of Assets on Web does not equal number of assets on local. Aborting data gathering.')
				print('%d assets on the web, %d asset on local' % (
					len(set(assets_on_web)),
					len(set(assets_on_local))))
				print('Asset(s) on web but not on local:')
				for aow in assets_on_web.keys():
					if aow not in assets_on_local.keys():
						print(aow)
				print('Asset(s) on local but not on web')
				for ail in assets_on_local.keys():
					if ail not in assets_on_web.keys():
						print(ail)
				sys.exit()
			if verbose:
				print('Verification complete.\n')

			# get the data for each asset from online
			if verbose:
				print('\nDownloading the data for each asset from the web ...')
				start_time = datetime.now()
			income_df      = sf.load('income',      variant='quarterly', market='us')
			balance_df     = sf.load('balance',     variant='quarterly', market='us')
			cashflow_df    = sf.load('cashflow',    variant='quarterly', market='us')
			shareprices_df = sf.load('shareprices', variant='daily',     market='us')
			if verbose:
				end_time = datetime.now()
				print('Downloads complete. Duration: %.1f minutes\n' % ((end_time - start_time).total_seconds() / 60.0))

			# format the data
			if verbose:
				print('\nFormatting the data for each asset ...')
				start_time = datetime.now()
			n  = len(assets_on_web.keys())
			bp = BlockPrinter()
			assets = {}
			for i, (ticker, url) in enumerate(assets_on_web.items()):
				filepath = assets_on_local[ticker] if assets_on_local != {} else \
					os.path.join(FMTD_DATA_PATH, ticker+'.csv')
				assets[ticker] = self.get_data_of_1_asset(
									ticker,
									income_df[income_df['Ticker'] == ticker],
									balance_df[balance_df['Ticker'] == ticker],
									cashflow_df[cashflow_df['Ticker'] == ticker],
									shareprices_df[shareprices_df['Ticker'] == ticker],
									save=True, filepath=filepath, append=True)
				if verbose:
					bp.print('Ticker %s:\tasset %d out of %d, %.1f %% complete.' % (
						ticker, (i+1), n, 100 * (i+1) / n))
			if verbose:
				end_time = datetime.now()
				print('Formatting complete. Duration: %.1f minutes\n' % ((end_time - start_time).total_seconds() / 60.0))
			sys.exit()

		elif source == 'local':

			if verbose:
				print('\nGetting the data for each asset from the local file system ...')
			assets_on_local = self.get_all_asset_names_and_locations('local')
			assets = {}
			for ticker, filepath in assets_on_local.items():
				assets[ticker] = pd.read_csv(filepath, index_col=[0])
			if verbose:
				print('Data aquired.\n')

		else:
			print('Invalid Argument: input into get_all_asset_names_and_location')
			print('Valid values: [\"web\", \"local\"]')
			print('Argument: \"source\" = %s' % source)
			sys.exit()

		return assets

	''' get_all_asset_names_and_locations
		Returns:
			assets: dictionary of ticker symbols (strings) and their location (strings)
				key = ticker symbol
				value = location (url if source='web', local file path if source='local')
		Arguments:
			source: string - string specifying where to get the data: valid_values: ['web', 'local']
		'''
	def get_all_asset_names_and_locations(self, source, verbose=False):

		if source == 'web':
			df = sf.load_companies(market='us') # download data
			assets_on_web = df.index.tolist() # get assets on web list
			assets = {ticker : '' for ticker in assets_on_web}
	
		elif source == 'local':
			base_filepath = FMTD_DATA_PATH
			assets = {}
			for filename in os.listdir(base_filepath):
				if os.path.isfile(os.path.join(base_filepath, filename)):
					ticker_name = '.'.join(filename.split('.')[:-1])
					filepath = os.path.join(base_filepath, filename)
					assets[ticker_name] = filepath
		
		else:
			print('Invalid Argument: input into get_all_asset_names_and_location')
			print('Valid values: [\"web\", \"local\"]')
			print('Argument: \"source\" = %s' % source)
			sys.exit()

		if verbose:
			print(len(assets))
			for tn, loc in assets.items():
				print('%s\t%s' % (tn, loc))
				input()
			
		return assets

	''' get_data_of_1_asset
		Returns:
			pandas dataframe of quarterly fundamental data of ticker
		Arguments:
			ticker - string - the ticker symbol of the asset to get data on
			url - string - the url where to get the data
			save - boolean - if you want to save the data
			filepath - string - local filepath to save data at (if save is True, filepath must be specified)
			append - boolean - if True, append the new data to the old data (append XOR overwrite must be True)
			overwrite - boolean - if True, overwrite the old data with the new data (append XOR overwrite must be True)
		'''
	def get_data_of_1_asset(self, ticker,
		income_df, balance_df, cashflow_df, shareprices_df,
		save=False, filepath=None, append=False, overwrite=False):

		df = income_df.copy()

		# the overlapping columns between 2 dataframes (aka the columns with same name)
		# need to have the same values for the dataframes to merge properly
		# if they don't, combine each overlapping col such that for each row:
		# if both rows have a nan value, use an nan value
		# if just one of them is nan, use the non nan value
		# if neither are nan, take the average
		def combine_overlapping_columns(df1, df2):
			df1 = df1.reset_index(drop=True)
			df2 = df2.reset_index(drop=True)
			overlapping_columns = list(set(df1.columns).intersection(set(df2.columns)))
			def combo(v1, v2):
				# print('combo %s, %s' % (v1, v2))
				try:
					if np.isnan(v1) and np.isnan(v2):
						# print('np.isnan(v1) and np.isnan(v2)')
						return v1
				except: pass
				try:
					if np.isnan(v1):
						# print('np.isnan(v1)')
						return v2
				except: pass
				try:
					if np.isnan(v2):
						# print('np.isnan(v1)')
						return v1
				except: pass
				if v1==v2:
					# print('v1==v2, returning v1')
					return v1
				if isinstance(v1, str) and isinstance(v2, str):
					# print('isinstance(v1, str) and isinstance(v2, str), returning v1')
					return v1 # idk what else you would return
				# print('sum(v1, v2) / 2')
				return v1#sum(v1, v2) / 2
			for col in overlapping_columns:
				if col != 'Quarter end' and df1[col].tolist() != df2[col].tolist():
					new_data = df1[col].combine(df2[col], combo).tolist()
					# print(1)
					# print(df1[col])
					# print(2)
					# print(df2[col])
					# print(3)
					# print(new_data)
					df1[col] = new_data
					df2[col] = new_data
			return df1, df2

		# convert "Fiscal Year" and "Fiscal Quarter" columns into "Quarter end" column with format: 'YYYY-MM-DD'
		def get_quarter_str(fiscal_period):
			if fiscal_period == 'Q1': return '-03-31'
			if fiscal_period == 'Q2': return '-06-30'
			if fiscal_period == 'Q3': return '-09-30'
			if fiscal_period == 'Q4': return '-12-31'

		df.insert(0, 'Quarter end',
			df['Fiscal Year'].astype(str) + \
			df['Fiscal Period'].apply(lambda p : get_quarter_str(p)))

		# get share prices at end of each quarter
		shareprices_df = shareprices_df[shareprices_df['Date'].isin(df['Quarter end'])][['Date', 'Close']].rename(
			columns={
				'Date'  : 'Quarter end',
				'Close' : 'Close Price'
			})
		df, shareprices_df = combine_overlapping_columns(df, shareprices_df)
		df = pd.merge(df, shareprices_df, on=list(set(df.columns).intersection(set(shareprices_df.columns))), how='outer')

		balance_df.insert(0, 'Quarter end',
			balance_df['Fiscal Year'].astype(str) + \
			balance_df['Fiscal Period'].apply(lambda p : get_quarter_str(p)))
		df, balance_df = combine_overlapping_columns(df, balance_df)
		df = pd.merge(df, balance_df,     on=list(set(df.columns).intersection(set(balance_df.columns))), how='outer')

		cashflow_df.insert(0, 'Quarter end',
			cashflow_df['Fiscal Year'].astype(str) + \
			cashflow_df['Fiscal Period'].apply(lambda p : get_quarter_str(p)))
		df, cashflow_df = combine_overlapping_columns(df, cashflow_df)
		df = pd.merge(df, cashflow_df,    on=list(set(df.columns).intersection(set(cashflow_df.columns))), how='outer')

		# drop uneccessary columns and make NaNs "None"
		df.drop(columns=['Ticker', 'SimFinId', 'Currency', 'Fiscal Year', 'Fiscal Period'], inplace=True)
		df.fillna('None', inplace=True)

		if save:

			if filepath == None:
				print('Invalid input to get_data_of_1_asset, if save equals True, filepath cannot equal None.')
				sys.exit()
			if not (append != overwrite):
				print('Invalid input to get_data_of_1_asset, if save equals True, append XOR overwrite must be True.')
				print('currently: append = %s and overwrite = %s' % (append, overwrite))
				sys.exit()

			if overwrite:
				df.to_csv(filepath)
			elif append:
				df = self.append_new_data_to_old_data(df, filepath)

		return df

	''' append_new_data_to_old_data
		Returns:
			pandas dataframe of old and new data combined
		Arguments:
			df - pandas dataframe - dataframe of new data
			filepath - string - local path to old data
		'''
	def append_new_data_to_old_data(self, df, filepath):
		try:
			df0 = pd.read_csv(filepath, index_col=[0])
			file_found = True
		except FileNotFoundError:
			file_found = False

		if file_found:

			# print('data from local\t', df0.shape)
			most_recent_quarter_df0 = df0['Quarter end'].iloc[0]

			# # verify the quarters line up
			# if not df['Quarter end'].isin([most_recent_quarter_df0]).any():
			# 	print('The most recent quarter in the old data is not in the new data.')
			# 	print('Aborting appending the new data to the old data.')
			# 	return df0
			''' NOTE:
				this is commented out because I decided if the quarters don't
				line up its better to get the data we CAN get, and have a gap.
				'''
			df = df[df['Quarter end'] > most_recent_quarter_df0]

			# # verify theres no NaN values in the new df
			# row_indeces_to_drop = []
			# for index, quarter_series in df.iterrows():
			# 	number_of_nans_this_quarter = \
			# 		quarter_series[quarter_series == 'None'].shape[0]
			# 	if number_of_nans_this_quarter > 0:
			# 		row_indeces_to_drop.append(index)
			# # if len(row_indeces_to_drop) > 0: # either drop everything if theres any "None" values
			# # 	print('\"None\" values in new data,')
			# # 	print('Aborting appending the new data to the current data.')
			# # 	return df0
			# df.drop(row_indeces_to_drop) # or only drop the rows with "None" values
			''' NOTE:
				this is commented out because I decided if there are "None" values
				in the new data its better to get the data we CAN get, and have a "None" values.
				'''

			# append, save, and return the new and old data
			df = df.append(df0, sort=False)
			df = df.reset_index(drop=True)

		df.to_csv(filepath)
		return df

	''' plot_data_quality_report
		Returns:
			None, it displays a plot showing the quality of the data for each quarter and each stock.
			The plot is a grid with each quarter along the horizontal axis and each stock listed along the vertical axis.
			Each stock has fundamental data for SOME of the quarters. The stocks are sorted by the number of quarters they
			have data for. The stock with data for the most number of quarters is at the top and the stock with data for
			the least number of quarters is at the bottom. For each quarter there are x fundamental data columns a stock
			can have data for. If a stock has data on 100% of its values that cell in the grid is GREEN; if it has 0 that 
			cell is RED, with a gradient inbetween depending on the percentage of data it has.
		Arguments:
			verbose - boolean - print to the console if True
		'''
	def plot_data_quality_report(self, verbose=True):

		# converts start and end quarters to proper end dates according to Google
		# Proper End Dates:
		# Q1   03/31
		# Q2   06/30
		# Q3   09/30
		# Q4   12/31
		def proper_end_date(date_str):
			y, m, d = tuple(date_str.split('-'))
			if '01-01' <= '-'.join([m, d]) <= '03-31': (m, d) = ('03', '31')
			if '04-01' <= '-'.join([m, d]) <= '06-30': (m, d) = ('06', '30')
			if '07-01' <= '-'.join([m, d]) <= '09-30': (m, d) = ('09', '30')
			if '10-01' <= '-'.join([m, d]) <= '12-31': (m, d) = ('12', '31')
			return '-'.join([y, m, d])
		# gets next proper quarter after date_str
		def next_quarter(date_str):
			y, m, d = tuple(date_str.split('-'))
			if '-'.join([m, d]) == '03-31': return '-'.join([y, '06', '30'])
			if '-'.join([m, d]) == '06-30': return '-'.join([y, '09', '30'])
			if '-'.join([m, d]) == '09-30': return '-'.join([y, '12', '31'])
			if '-'.join([m, d]) == '12-31': return '-'.join([str(int(y)+1), '03', '31'])
		# creates list of proper quarters
		def get_quarters(assets, verbose=True):

			if verbose: print('\nGetting Quarter range ...')

			# create list of all quarters
			# from earliest to latest quarter of all the assets
			earliest_quarter = assets[list(assets.keys())[0]]['Quarter end'].min()
			latest_quarter   = assets[list(assets.keys())[0]]['Quarter end'].max()
			for i, (ticker, df) in enumerate(assets.items()):
				if df.shape[0] == 0: continue
				latest_quarter = df['Quarter end'].iloc[0] \
					if df['Quarter end'].iloc[0] > latest_quarter else \
						latest_quarter
				earliest_quarter = df['Quarter end'].iloc[-1] \
					if df['Quarter end'].iloc[-1] < earliest_quarter else \
						earliest_quarter

			# convert start and end quarters to proper end dates according to Google
			earliest_quarter = proper_end_date(earliest_quarter)
			latest_quarter   = proper_end_date(latest_quarter)

			# create list of all quarters
			quarters = []
			q = earliest_quarter
			while q <= latest_quarter:
				quarters.append(q)
				q = next_quarter(q)
			num_quarters = len(quarters)

			if verbose:
				print('Quarter Range aquired.')
				print('	earliest_quarter = %s' % earliest_quarter)
				print('	latest_quarter   = %s' % latest_quarter)
				print('	covering %d quarters, aka %.2f years\n' % (num_quarters, (num_quarters / 4)))

			return quarters, num_quarters, earliest_quarter, latest_quarter
		# get data coverage percentage each quarter for each asset (in 2D array)
		def calculate_data_coverage(assets, quarters, verbose=True, save=True):

			if verbose:
				print('\nCalculating data coverage for each asset for each quarter ...')
				start_time = datetime.now()
			number_of_cols_in_dfs = set(map(lambda df : df.shape[1], list(assets.values())))
			if len(number_of_cols_in_dfs) != 1:
				print('Not all the CSV files have the same number of columns.')
				print('Number of columns in CSV files:' % number_of_cols_in_dfs)
				print('Aborting creating data quality report.')
				sys.exit()
			x = list(number_of_cols_in_dfs)[0] - 1 # x = total number of fields (minus the "Quarter end" field)
			data_coverage = {}
			bp = BlockPrinter()
			n  = len(assets.keys())
			for i, (ticker, df) in enumerate(assets.items()):
				if verbose:
					bp.print('Ticker %s:\tasset %d out of %d, %.1f %% complete.' % (
						ticker, (i+1), n, 100 * (i+1) / n))
				ticker_data_coverage = []
				number_of_quarters_covered = 0
				ticker_proper_quarters_series = df['Quarter end'].apply(lambda q : proper_end_date(q))
				for q in quarters:
					try:
						j = ticker_proper_quarters_series[ticker_proper_quarters_series == q].index[0]
					except:
						j = None
						number_of_data_points_this_quarter = 0
					if j != None:
						quarter_series = df.iloc[j].drop(labels=['Quarter end'])
						number_of_data_points_this_quarter = \
							quarter_series[quarter_series != 'None'].shape[0]
						number_of_quarters_covered += 1

					ticker_data_coverage.append(number_of_data_points_this_quarter)
				data_coverage[ticker] = (number_of_quarters_covered, ticker_data_coverage)

			# sort them by number_of_quarters_covered
			data_coverage = OrderedDict(sorted(data_coverage.items(), key=lambda x : x[1]))
			data_coverage_2D_array = [ticker_data_coverage for ticker, (number_of_quarters_covered, ticker_data_coverage) in data_coverage.items()]

			if save:
				json.dump(data_coverage, open(PLOT_DATA_PATH, 'w'))

			if verbose:
				end_time = datetime.now()
				print('Calculations complete. Duration: %.1f minutes\n' % ((end_time - start_time).total_seconds() / 60.0))

			return data_coverage, data_coverage_2D_array
		def get_data_coverage_from_file():
			data_coverage		  = json.load(open(PLOT_DATA_PATH, 'r'))
			data_coverage_2D_array = [ticker_data_coverage for ticker, (number_of_quarters_covered, ticker_data_coverage) in data_coverage.items()]
			return data_coverage, data_coverage_2D_array


		assets = self.get_data_of_all_assets('local')
		num_assets = len(assets.keys())
		num_fields = list(assets.values())[0].shape[1]
		cols = list(assets.values())[0].columns
		print(cols)
		print(len(cols))

		quarters, num_quarters, earliest_quarter, latest_quarter = \
			get_quarters(assets, verbose=verbose)
		# data_coverage_dct, data_coverage_2D_array = calculate_data_coverage(assets, quarters)
		data_coverage_dct, data_coverage_2D_array = get_data_coverage_from_file()

		# plot the data coverage
		if verbose:
			print('\nPlotting data coverage ...')
		fig, ax = plt.subplots()#figsize=(12, 6.5))
		fig.canvas.set_window_title(self.report_name)
		mng = plt.get_current_fig_manager()
		mng.resize(*mng.window.maxsize()) # go fullscreen
		red_to_green_cmap = mcolors.LinearSegmentedColormap.from_list('', ['red', 'yellow', 'green'])
		# colormaps: https://matplotlib.org/devdocs/tutorials/colors/colormaps.html#list-colormaps
		plot = ax.pcolormesh(data_coverage_2D_array, cmap='RdYlGn')#'RdBu')#red_to_green_cmap)
		ax.set_title(
			'Data Coverage of Fundamental Data of %d Stocks over %d Quarters (%.2f Years)' % (
			num_assets,
			num_quarters,
			(num_quarters / 4)),
			fontsize=14)
		ax.set_ylabel('%d Stocks (sorted from least to most coverage)' % num_assets)
		ax.set_yticks([])
		ax.set_xlabel('Quarters')
		years = sorted(set(map(lambda q : q.split('-')[0], quarters)))
		years_x_loc = []
		for y in years:
			# year x loc goes at beginning of quarter
			quarters_in_year = list(filter(lambda q : q.split('-')[0] == y, quarters))
			q1 = min(quarters_in_year)
			years_x_loc.append(quarters.index(q1))
		mry   = int(latest_quarter.split('-')[0]) # mry = most recent year
		years = list(map(lambda y : y if (mry-int(y))%5==0 else '', years))
		ax.set_xticks(years_x_loc)
		ax.set_xticklabels(years)

		# format labels appear when hoving over a point
		# source: https://stackoverflow.com/questions/7908636/possible-to-make-labels-appear-when-hovering-over-a-point-in-matplotlib
		def format_coord(x, y):
			ticker = list(data_coverage_dct.keys())[int(y)]
			quarter = quarters[int(x)]
			_y, _m, _d = tuple(quarter.split('-'))
			quarter_label = '%s Q%d' % (_y, (int(_m) / 3))
			# data_coverage_this_quarter = data_coverage_dct[ticker][]
			num_quarters_with_nonzero_coverage = data_coverage_dct[ticker][0]
			quarter_values_with_nonzero_coverage = \
				list(filter(lambda coverage : coverage > 0.0, data_coverage_dct[ticker][1]))
			data_coverage_average_of_all_non_zero_quarters = \
				float(sum(quarter_values_with_nonzero_coverage)) / len(quarter_values_with_nonzero_coverage) \
				if len(quarter_values_with_nonzero_coverage) > 0 else 0.0
			percent_of_quarters_with_nonzero_data_coverage = \
				100.0 * float(num_quarters_with_nonzero_coverage) / num_quarters
			current_quarter_coverage = data_coverage_dct[ticker][1][int(x)]
			current_quarter_coverage_pct = 100 * float(current_quarter_coverage) / num_fields
			s1 = "Stock %d / %d: %s%s" % (int(y)+1, num_assets, ticker, ' '*(6-len(ticker)))
			s2 = "Quarter: %s, %d / %d fields (%.1f%%) are covered" % (quarter_label, current_quarter_coverage, num_fields, current_quarter_coverage_pct)
			s3 = "%d / %d quarters (%.1f%%) have data." % (num_quarters_with_nonzero_coverage, num_quarters, percent_of_quarters_with_nonzero_data_coverage)
			s4 = "Data's average coverage: %.1f%%." % (data_coverage_average_of_all_non_zero_quarters)
			return '\t'.join([s1, s2, s3, s4])
		ax.format_coord = format_coord

		# legend
		# source: https://stackoverflow.com/questions/32462881/add-colorbar-to-existing-axis
		divider = make_axes_locatable(ax)
		cax = divider.append_axes('right', size='5%', pad=0.10)
		tick_locs = np.linspace(0, num_fields-1, 5) # why there should be -1 idk, but without it the top tick disappears
		cbar = fig.colorbar(
			plot,
			cax=cax,
			orientation='vertical')
		cbar.ax.set_ylabel('Percent Data Coverage (out of %d fields)' % num_fields, fontsize=12)
		cbar.set_ticks(tick_locs)
		cbar.ax.set_yticklabels(['0 %', '25 %', '50 %', '75 %', '100 %'])


		plt.show()
		if verbose:
			print('Plot complete.\n')




if __name__ == '__main__':

	simfin_scrapper = SimFinScrapper()

	# assets = simfin_scrapper.get_data_of_all_assets('web')
	simfin_scrapper.plot_data_quality_report()


