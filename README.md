# trading-setup


# Exchanges

poloniex - crypto price data
	doesn't service US citizens anymore though :(
	0.25% trading fee
	has margin trading with max 2x leverage
	does provide an API

alpaca - stock price and fundamental data
	services US citizens!
	has no trading fee, except $0.02 SEC fee
	has margin trading with max 4x leverage
	does provide an API

kraken - crypto price data
	services US citizens!
	0.26% trading fee
	has margin trading with max 5x leverage
	does provide an API

coinbase pro - crypto price data
	services US citizens!
	0.50% trading fee
	doesnt have margin trading
	does provide an API


# Setup

copy the file api_keys_TEMPLATE.json into a new file and name it api_keys.json

go to the website(s) for the exchange(s) you plan to use, create an account, and get whatever api keys, endpoints, etc. that you need

open the file and enter the keys into their corresponding location (based on exchanges and stuff)
	(the .gitignore file keeps api_keys.json from getting put online)



