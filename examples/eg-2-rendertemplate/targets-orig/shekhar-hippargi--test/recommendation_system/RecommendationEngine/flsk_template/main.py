from flask import Flask
from flask import render_template, request

import os
from io import StringIO

import pandas as pd

UPLOAD_FOLDER = '/home/dkalathiya/Work/trainingassignment/Dhruvesh/TimeSeriesAPI/data'
ALLOWED_EXTENSIONS = {'txt', 'csv'}

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('index.html')
    elif request.method == 'POST':
        if (request.files['file'].filename != "") and (request.form["algoname"]) and allowed_file(
                request.files['file'].filename):
            algo_name = request.form["algoname"]
            file = request.files['file']

            # You, now, have algo_name and File which you can pass to pd.read_csv() and train your model.

            return "output"
        else:
            return "In-appropriate File passed...!"


if __name__ == '__main__':
    app.run(debug=True)
