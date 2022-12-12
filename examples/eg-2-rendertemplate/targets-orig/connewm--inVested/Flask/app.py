# app.py
import json

from flask import Flask
from flask import request, render_template, jsonify, g

import sys
import os
from datetime import datetime, timedelta

from retrieve_data import *
from assistant import *

# Create the instance of assitant to use
vested_assistant = watson_assistant()

# Get date information to use in API calls
today = datetime.today()
yesterday = today - timedelta(days=1)
lastweek = today - timedelta(days=7)

# define date-related conversion functions
def format_month(month_num):
  # convert numeric month to string
  switch_month = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec"
  }
  
  return switch_month.get(month_num, "Error")

# convert year from format XXXX to YY
def format_year(year):
  return str(year % 100)

# Folder locations for frontend files
app = Flask(__name__, static_folder="../React/build/static", template_folder="../React/build")

# base path, render according to react-generated html file
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# catch all route to keep users on react single page
@app.route('/<path:path>', methods=['GET'])
def any_root_path(path):
    return render_template('index.html')

@app.route("/api/get_watson_response", methods=["POST"])
def get_watson_response():
  # get the request from the POST in JSON format
  incoming = request.get_json()

  # extract the message from the JSON
  message = incoming.get('message')

  # call Watson Assistant API (message)
  response = vested_assistant.get_watson_response(message)

  # return Watson response
  return (response)

# route to fetch company data from the API
@app.route("/api/get_company_data", methods=["POST"])
def get_company_data():
    # get the request from the POST in JSON format
    incoming = request.get_json()

    # extract the company from the JSON
    comp = incoming.get('company')

    # TODO: get month from client side, month format: XYZ (three letter abbreviation of month)
    # TODO: get day from client side, day format: XY
    # TODO: get year from client side, year format: XY (implicit -> only supports 2000 onward)
    startDate = format_month(lastweek.month)+str(lastweek.day)+format_year(lastweek.year)
    endDate = format_month(today.month)+str(today.day)+format_year(today.year)

    # create data retrieval object for company
    google = retrieve_data(comp, startDate, endDate)

    # get data for company
    data = google.get_company_data()

    # serialize obj to JSON
    data = json.loads(data)

    return(jsonify(data))

# route to fetch company data from the API
@app.route("/api/get_historical_data", methods=["POST"])
def get_historical_data():
    # get the request from React in JSON format
    incoming = request.get_json()

    # extract the company from the JSON
    comp = incoming.get('company')

    endDate = format_month(today.month)+str(today.day)+format_year(today.year)
    startDate = format_month(lastweek.month)+str(lastweek.day)+format_year(lastweek.year)

    # create data retrieval object for company
    historical = retrieve_data(comp, startDate, endDate)

    # get data for company
    data = historical.get_historic_data()

    # serialize obj to JSON
    data = json.loads(data)

    return(jsonify(data))

print('Starting Flask!')

# for local dev ONLY
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80)
