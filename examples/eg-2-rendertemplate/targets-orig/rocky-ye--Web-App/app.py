from src.predict import predicting
import argparse

import traceback
from flask import render_template, request, redirect, url_for
import logging.config
# from app.models import Tracks
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from src.create_database import Insurance
import config.flaskconfig as config
# Initialize the Flask application

app = Flask(__name__, template_folder="app/templates")
import pandas as pd

# Configure flask app from flask_config.py
app.config.from_pyfile('config/flaskconfig.py')


# Define LOGGING_CONFIG in flask_config.py - path to config file for setting
# up the logger (e.g. config/logging/local.conf)
logging.config.fileConfig(app.config["LOGGING_CONFIG"])
logger = logging.getLogger(app.config["APP_NAME"])
logger.debug('Test log')

# Initialize the database
db = SQLAlchemy(app)

@app.route('/')
def index():
    """Main view that lists songs in the database.

    Create view into index page that uses data queried from Track database and
    inserts it into the msiapp/templates/index.html template.

    Returns: rendered html template

    """

    try:
        data = db.session.query(Insurance).limit(app.config["MAX_ROWS_SHOW"]).all()
        logger.debug("Index page accessed")
        return render_template('index.html', insurances=data, result=config.RESULT)
    except:
        traceback.print_exc()
        logger.warning("Not able to display tracks, error page returned")
        return render_template('error.html')


@app.route('/add', methods=['POST'])
def add_entry():
    """View that process a POST with new song input

    :return: redirect to index page
    """

    try:
        insurance1 = Insurance(
                            age=request.form['age'],
                              sex=request.form['sex'],
                              bmi=request.form['bmi'],
                              children=request.form['children'],
                              smoker=request.form['smoker'],
                              region=request.form['region'],
                               charges= None
                              )
        db.session.add(insurance1)
        db.session.commit()
        logger.info("New recorded added to the database")
        col = ['age','sex','bmi','children','smoker','region']
        newData = pd.DataFrame([[
            request.form['age'],
            request.form['sex'],
            request.form['bmi'],
            request.form['children'],
            request.form['smoker'],
            request.form['region'],
        ]], columns=col)

        config.RESULT = predicting(newData)

        return redirect(url_for('index'))
    except Exception as e:
        # logger.warning("Not able to display tracks, error page returned. %s", e)
        config.RESULT = 'Please_enter_all_information_correctly!'
        # return render_template('error.html')
        return redirect(url_for('index'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Running the app")
    parser.add_argument('--local', '-i', action='store_true', help='connect to local database')
    args = parser.parse_args()
    if args.local:
        config.LOCAL_DB = True
        logger.info('Connecting to local database.')
    if config.LOCAL_DB:
        app.config['SQLALCHEMY_DATABASE_URI'] = config.LOCAL_SQLALCHEMY_DATABASE_URI
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI

    app.run(debug=app.config["DEBUG"], port=app.config["PORT"], host=app.config["HOST"])