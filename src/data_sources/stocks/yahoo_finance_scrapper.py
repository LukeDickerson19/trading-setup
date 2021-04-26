


'''


TO DO:

	find good api for yahoo finance
		or somewher that provides the data required

	see if you can use flutter
		need to connect to the api
			if dart has like an api like python requests library it wouldn't matter what language the api was in
		and run it locally, check

	data required
		dividend history
		quarterly revenue
			aka money made this year
		quarterly expenses
			aka money spent this year
		total value of all assets
			aka capital of any kind
				aka money or the resale value of anything they own
					physical or digital
		total value of all liabilities
			aka debts

	make the scrapper run every day
		and compare the latest value for each company and compare it to the database
		and update the database if there's anything new
		
			this has to be done instead of just running the scrapper quarterly because some companies
			release info on different days of the year

		it would probably be a good idea to store it in a mysql db

	plots to make

		plot 1
			dividends per quarter by itself

			to make sure theres a steady growth of dividends

		plot 2
			total asset value above horizontal line
				with quarterly revenue stacked on top of it
			total liabilities value below horizontal line
				with quarterly expenses and dividends stacked on top

			to make sure they're handling their debts effectively
			have stable revenue
			are growing their total asset value

		plot 3
			net value of all of those things combined
				aka
					(total asset value + quarterly revenue) - (total liability value + quarterly expenses + dividends) = net valuation
			net valuation dividend by number of shares maybe
				is this how book value is calculated?
			current market price
			
	it would be interesting to see what companies like tesla look like with this software
		amazon
		microsoft
		tesla
		facebook
		google

		it would also be cool  if you could classify them by sector and country



