from flask import Flask, render_template, url_for, redirect, request
import datetime
import pricepredict
import pandas as pd
import os

app = Flask(__name__)

@app.route("/")
def home():
	return render_template("home.html")


@app.route("/dashboard", methods = ['GET'])
def dashboard():
	return render_template('dashboard.html')


@app.route("/dashboard", methods = ['POST'])
def getStockData():
	#Retrieve symbol from html form
	symbol = request.form["sym"]

	#PLot data from Alpha Vantage
	#plotData(enteredSymbol)

	graph_path = None
	return render_template('dashboard.html', graph='./static/images/plot.png')



@app.route("/pricepredict", methods = ['GET'])
def PricePredictHome():
	return render_template('pricepredict.html', graph=None)


@app.route("/pricepredict", methods = ['POST'])
def PricePredict():
	showButton=False
	try:
		symbol = request.form["sym"]
	except:
		symbol = 'GOOGL'

	try:
		runAlgorithm = bool(request.form["runAlgorithm"])
		forecast_period = int(request.form["forecast_period"])

	except:
		runAlgorithm = False
		forecast_period = 365


	if runAlgorithm:
		data_path = pricepredict.get_data(symbol)
		data = pd.read_csv(data_path)
		forecast_decision, path_to_graph = pricepredict.predict(data, forecast_period, symbol)
		if forecast_decision:
			decision = 'BUY!'
		else:
			decision = 'SELL!'

		return render_template('pricepredict.html', 
						   graph=path_to_graph,
						   showButton=False,
						   decision=decision,
						   symbol=symbol,
						   forecast_period=forecast_period)

	elif os.path.isfile(f'./static/images/{symbol}.png'):
		path_to_graph = f'./static/images/{symbol}.png'
		#if it exists, show button and avoid recomputation
		return render_template('pricepredict.html', 
							   graph=path_to_graph,
							   showButton=True,
							   decision=None,
							   symbol=symbol,
							   forecast_period=forecast_period)
	else:
		data_path = pricepredict.get_data(symbol)
		data = pd.read_csv(data_path)
		forecast_decision, path_to_graph = pricepredict.predict(data, forecast_period, symbol)
		if forecast_decision:
			decision = 'BUY!'
		else:
			decision = 'SELL!'

		return render_template('pricepredict.html', 
						   graph=path_to_graph,
						   showButton=False,
						   decision=decision,
						   symbol=symbol,
						   forecast_period=forecast_period)
		


if __name__ == "__main__":
	app.run(debug=True)

	'''
			data = pd.read_csv(path_to_graph)
		if data['yhat'].values[-1] > data['yhat'].values[-forecast_period]:
			decision = 'BUY!'
			'''