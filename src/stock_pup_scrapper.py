import pandas as pd
import requests
import urllib.request
from bs4 import BeautifulSoup as bs
import sys, os, time
import numpy as np




def download_financial_data(directory):
	downloads = download_names_and_urls() # makes 1 call to stockpup server
	# print_company_tickers(downloads)
	download_csv_files(downloads, directory) # makes hundreds of calls to stockpup server
def download_names_and_urls():
	# get urls of the csv files to download
	_URL  = 'http://www.stockpup.com/data/'
	r = requests.get(_URL)
	soup = bs(r.text, 'lxml')
	urls, names = [], []
	for i, link in enumerate(soup.findAll('a')):
		href = link.get('href')
		if href and href.endswith('_quarterly_financial_data.csv'):
			url = _URL[:len(_URL)-len('/data/')] + href
			urls.append(url)
			name = href[len('/data/'):len(href)-len('_quarterly_financial_data.csv')] + '.csv'
			names.append(name)
			# names.append(soup.select('a')[i].attrs['href'][len('/data/'):])
	return zip(names, urls)
def download_csv_files(downloads, directory):
	print('Downloading financial data for companies:')
	for name, url in downloads:
		print('\t%s' % name)
		download_csv_file(url, name, directory)
def download_csv_file(url, filename, directory):
	rq = urllib.request.Request(url)
	res = urllib.request.urlopen(rq)
	csv = open(os.path.join(directory, filename), 'wb')
	csv.write(res.read())
	csv.close()
	time.sleep(2.5) # don't overload server
def print_company_tickers(downloads):
	print('Company Tickers:')
	for name, url in downloads:
		print('%s' % name[:len(name)-len('.csv')])

def get_financial_data_from_CSVs(directory, companies, all_companies=False):

	# source: https://stackoverflow.com/questions/20906474/import-multiple-csv-files-into-pandas-and-concatenate-into-one-dataframe
	# return pd.concat(
	# 	pd.read_csv(
	# 		os.path.join(directory, filename)
	# 	)
	# 	for filename in os.listdir(directory)
	# )

	# source: https://stackoverflow.com/questions/28368598/dataframe-of-dataframes-with-pandas
	print('Reading quarterly financial data from csv files')
	print('for: %s ...' % (companies if not all_companies else 'all companies'))
	dictionary = {}
	for filename in os.listdir(directory):
		name = filename[:len(filename)-len('.csv')]
		if name in companies or all_companies:
			df = pd.read_csv(os.path.join(directory, filename))
			# these were the only characters that needed to be changed from looking
			# at the data in order to make the columns machine friendly (i.e. no spaces symbols)
			new_cols = {}
			for col in list(df):
				new_col = col.replace(' ', '_')
				new_col = new_col.replace('&','and')
				new_col = new_col.replace('/','')
				new_cols[col] = new_col
			df.rename(columns=new_cols, inplace=True)
			dictionary[name] = df
	# return pd.concat(dictionary)
	return dictionary

if __name__ == '__main__':

	# determine path to directory where data is stored
	directory = os.getcwd()
	directory = directory[:len(directory)-len('wsm-machine/src/data_gathering')]
	directory += 'data/quarterly_financial_data/'

#	download_financial_data(directory)

	# returns dictionary of pandas data frames
	financial_data = get_financial_data_from_CSVs(directory, [], all_companies=True)
	
	print(financial_data['A'])


