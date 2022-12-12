"""
Connect to robinhood api, save file as IO, then store in postgres database

device token: "8f0274a5-9c8e-4fdb-9252-387e631f6a28"

Settings for connecting to postgres
helpful links
https://realpython.com/flask-by-example-part-2-postgres-sqlalchemy-and-alembic/
https://stackoverflow.com/questions/31645550/why-psql-cant-connect-to-server

follow along from this site to create a user if desired, afterwards, edit user.yaml
https://www.digitalocean.com/community/tutorials/how-to-install-and-use-postgresql-on-ubuntu-16-04

creating postgresql database from bash (for postgres user after setting up user and password)
    sudo -u postgres createdb pensieve

open postgresql interface to database
    psql -d pensieve

creating table in database for connection (within psql)
    CREATE TABLE amazon_sellers (index serial PRIMARY KEY, seller_price text, company_name text, title text, asin text, product_price text, date date);

starting postgresql service once user, database, and table have been created
    sudo service postgresql status/start/restart/stop
"""

#from bs4 import BeautifulSoup   # create soup from webpage-object
import os
import re
import datetime
import argparse
import numpy as np
import pandas as pd
#import psycopg2
#from flask_sqlalchemy import SQLAlchemy
#from sqlalchemy.orm import sessionmaker, scoped_session
#from sqlalchemy import create_engine

from io import StringIO
from csv import writer

import yaml # conda install pyyaml

# relative import
from .Robinhood import Robinhood
from .login_data import collect_login_data


def initialize():

    with open("Application/programs/user.yaml", 'r') as stream:
        credentials = yaml.safe_load(stream)
    
    parser = argparse.ArgumentParser(
        description='Export Robinhood trades to a CSV file')
    parser.add_argument(
        '--debug', action='store_true', help='store raw JSON output to debug.json')
    parser.add_argument(
        '--username', default=credentials['robinhood']['username'], help='your Robinhood username')
    parser.add_argument(
        '--password', default=credentials['robinhood']['password'], help='your Robinhood password')
    parser.add_argument(
        '--mfa_code', help='your Robinhood mfa_code')
    parser.add_argument(
        '--device_token', default=credentials['robinhood']['device_token'], help='your device token')
    parser.add_argument(
        '--profit', action='store_true', help='calculate profit for each sale')
    parser.add_argument(
        '--dividends', action='store_true', help='export dividend payments')
    '''
    parser.add_argument(
        'run', help='flask dependent parser quirk?')
    '''
    print("initializing\n")
    args = parser.parse_args()
    print("initializing2\n")
    

    username = args.username
    password = args.password
    mfa_code = args.mfa_code
    device_token = args.device_token

    print("Bypassing protocols. Please wait...")

    robinhood = Robinhood()

    # login to Robinhood
    logged_in = collect_login_data(robinhood_obj=robinhood, username=username, password=password, device_token=device_token, mfa_code=mfa_code)

    return robinhood


class StockConn:
    
    def __init__(self, symbols=None):

        # resulting dataframe
        self.S2 = pd.DataFrame()
        
        # initialize user
        self.robinhood = initialize()

        # default to get symbols from watchlist
        if (symbols == None):
            self.symbols_dict = {} # fills out in get_watchlist
            self.symbols = self.get_watchlist()

        else:
            # key and value are the same for comma separated string of symbols
            self.symbols_dict = dict(zip(symbols.split(','), symbols.split(',')))
            self.symbols = symbols


    def query_instruments(self, results):
        instrument_arr = []
        for instrument_dict in results['results']:
            instrument = instrument_dict['instrument'].split('/')[-2]
            instrument_arr.append(instrument)

        return instrument_arr


    def get_watchlist(self):
        # get watchlist as an instrument id
        custom_endpoint = "https://api.robinhood.com/watchlists/Default/"
        query = self.robinhood.get_custom_endpoint(custom_endpoint)
        instruments = self.query_instruments(query)

        # clear watchlist
        self.symbols_dict = {}
        
        # convert instrument id to sticker and simple name
        i = 0
        for instrument in instruments:
            custom_endpoint = "https://api.robinhood.com/instruments/" + instrument
            query = self.robinhood.get_custom_endpoint(custom_endpoint)

            self.symbols_dict[query['symbol']] = query['simple_name']
            if i > 2:
                #break
                pass
            i += 1
        
        self.symbols = ','.join(self.symbols_dict.keys())
            
        return self.symbols


    def get_stocks_df(self, interval='day', span='year', bounds='regular'):
        
        print("symbols_str:", self.symbols)
        query_custom_history = 'https://api.robinhood.com/quotes/historicals/?symbols=' + self.symbols + '&interval=' + interval + '&span=' + span + '&bounds=' + bounds
        query = self.robinhood.get_custom_endpoint(query_custom_history)['results']

        #print("historical stock info", query)

        S2 = pd.DataFrame()
        for stock in query:
            #print(" ******* stock:", stock)
            stock_symbol = stock['symbol']
            historicals = stock['historicals']
            temp_date, temp_close_price = [], []
            S3 = pd.DataFrame()
            for day in historicals:
                temp_date.append(day['begins_at'])
                temp_close_price.append(day['close_price'])

            S3['date'] = temp_date
            S3['close_price'] = temp_close_price
            S3['symbol'] = stock_symbol
            S3['simple_name'] = self.symbols_dict[stock_symbol]

            S2 = pd.concat([S2, S3], axis=0)

        return S2

if __name__ == "__main__":

    initialize()
