# Importing flask module in the project is mandatory
# An object of Flask class is our WSGI application.
from flask import Flask, request, render_template
from flask_cors import CORS, cross_origin
from python.main import get_data_from_ticker_list
import json
import requests

# Flask constructor takes the name of
# current module (__name__) as argument.
app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

# The route() function of the Flask class is a decorator,
# which tells the application which URL should call
# the associated function.
@app.route('/')
@cross_origin()
# ‘/’ URL is bound with hello_world() function.
def hello_world():
  return render_template('index.html')

@app.route('/winners_from_list', methods=['POST'])
def winners_from_list():
  ticker_json = request.get_json()
  print(ticker_json)

  winners, data = get_data_from_ticker_list(ticker_json)
  return json.dumps(dict(winners))
 
@app.route('/page_html', methods=['GET'])
def page_html():
    ticker = request.args.get('ticker')
    headers =  {
      'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36',
      'Content-Type': 'text/html',
    }
    response = requests.get(f'https://finance.yahoo.com/quote/{ticker}/chart', headers=headers)
    return response.text


# main driver function
if __name__ == '__main__':
 
    # run() method of Flask class runs the application
    # on the local development server.
    app.run()