from flask import Flask, render_template, url_for, redirect, request
import datetime
import pricepredict
import pandas as pd

app = Flask(__name__)

@app.route("/")
def home():
	return render_template("home.html")


@app.route("/dashboard", methods = ['GET'])
def dashboard():
	return render_template('dashboard.html')


@app.route("/dashboard", methods = ['POST'])
def getStockData():
	#Retrieve symbol from form
	symbol = request.form["sym"]

	#plotData(enteredSymbol)

	graph_path = None
	return render_template('dashboard.html', graph='./static/images/plot.png')
	# return redirect(url_for('chart'))
	# return render_template('dashboard.html', sym=symbol)
	# TODO: setup chart display 


@app.route("/pricepredict", methods = ['GET'])
def PricePredictHome():
	return render_template('pricepredict.html', graph=None)


@app.route("/pricepredict", methods = ['POST'])
def PricePredict():
	symbol = request.form["sym"].upper()
	try:
		forecast_period = int(request.form["forecast_period"])
	except:
		forecast_period = 365
	data_path = pricepredict.get_data(symbol)
	data = pd.read_csv(data_path)

	forecast_decision,graph_path,current_price,current_date,predicted_price,forecast_date = pricepredict.predict(data, forecast_period, symbol)

	if forecast_decision:
		decision = 'BUY!'
	else:
		decision = 'SELL!'
	return render_template('pricepredict.html', 
						   graph=graph_path,
						   decision=decision,
						   forecast_period = forecast_period,
						   symbol=symbol,
						   current_price=round(current_price, 2),
						   current_date=current_date,
						   predicted_price=round(predicted_price, 2),
						   forecast_date=forecast_date)


if __name__ == "__main__":
	app.run(debug=False)