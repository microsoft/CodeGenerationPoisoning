#!/usr/bin/env python

from ticker import *
from time import sleep
import logging

from time import sleep
from flask import Flask, render_template
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/stream')
def stream():
    def generate():
        with open('main_scraper.log') as f:
            while True:
                yield f.read()
                sleep(1)

    return app.response_class(generate(), mimetype='text/plain')



def create_logger():
    logger = logging.getLogger('main_scraper')
    logger.setLevel(logging.INFO)
    # create file handler which logs even debug messages
    fh = RotatingFileHandler('main_scraper.log', maxBytes=32000, backupCount=1)
    fh.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("Main_scraper started")
    logger.debug("Main_scraper started")
    logger.error("Main_scraper started")

# todo, add automatic updates: https://hackthology.com/how-to-write-self-updating-python-programs-using-pip-and-git.html
task_4sec = Ticker_Scheduler(update_period_s=4,
                             callback_list=[get_kraken_orderdepth],
                             taskname='4s tasks')


task_5min = Ticker_Scheduler(update_period_s=60 * 5, callback_list=[get_coinmarketcap2,
                                                                    get_fear_greed_index,
                                                                    get_global_cap_v2,
                                                                    get_bitcoincharts_data,
                                                                    get_bitcoin_fees,
                                                                    get_blockchain_stats],
                             taskname='5min tasks')
task_15min = Ticker_Scheduler(update_period_s=60*15, callback_list= [get_kraken_trades],
                              taskname='15min_tasks')

task_60min = Ticker_Scheduler(update_period_s=60 * 60, callback_list=[get_news_data,
                                                                      get_bitcoincharts_data],
                              taskname='60min tasks')
if __name__ == "__main__":
    init_mongodb()
    create_logger()
    task_5min.start_thread()
    task_15min.start_thread()
    task_60min.start_thread()
    task_4sec.start_thread()
    app.run(host='0.0.0.0')
    while 1:
        sleep(20)
