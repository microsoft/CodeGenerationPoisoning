from flask import Flask, render_template, request,jsonify
import os
import pandas as pd
import numpy as np
import hyperopt
import xgboost
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
import warnings

from adv_algos import svm, randomforest

warnings.filterwarnings("ignore")
from basicalgos import basicalgos
import threading as th
from clean import cleaning
params = {}
app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')
    '''
    models=['Linear Regression','Logistic Regression','Polynomial Regression','Stepwise Regression','Ridge Regression','Lasso Regression','ElasticNet Regression']
    return render_template('base.html',models=models)
    '''
@app.route('/recommender')
def rec():
    return render_template('recommend.html')

@app.route('/Linear_Regression')
def linear():
    return render_template('Linear_Regression.html')

@app.route('/Polynomial_Regression')
def polynomial():
    return render_template('Polynomial_Regression.html')

@app.route('/Stepwise_Regression')
def stepwise():
    return render_template('Stepwise_Regression.html')

@app.route('/Ridge_Regression')
def ridge():
    return render_template('Ridge_Regression.html')

@app.route('/Lasso_Regression')
def lasso():
    return render_template('Lasso_Regression.html')

@app.route('/Elasticnet_Regression')
def elastic():
    return render_template("Elasticnet_Regression.html")

@app.route('/Dataset')
def dataset():
    return render_template('data.html')

@app.route('/algorithm/<name>')
def dynamic(name):
    return render_template('dynamic.html',name=name)

@app.route('/dashboard')
def dashboard():
    params["features"] = {'a': 90, 'b': 20, 'c': 33, "d": 40}
    return render_template('dashboard.html',params=params)

@app.route('/data')
def data():
    return jsonify(params)

@app.route('/success', methods=['POST'])
def success():
    # ML code to be written here
    if request.method == 'POST':
        data = request.files["dataset"]
        ordinal = request.form["ordinal_columns"]
        target = request.form["target"]
        print(target)
        print(ordinal)
        data.save(data.filename)
        print(str(data.filename))
        h = str(data.filename)
        ans = os.path.join(os.path.dirname(__file__), h)
        print(ans)

        data = pd.read_csv(ans)
        scaler = MinMaxScaler()
        params["nullcount"] = 0
        params["feat_count"] = 0
        params["best_acc"] = 0
        params["rows"] = 0
        params["features"] = {}
        params["algorithms"] = {"ridge": 0, "lasso": 0, "lasso_lars": 0, "elasticnet": 0, "knn": 0, "decisiontree": 0,"svm":0,"randomforest":0}

        X = data.drop(target,axis=1)
        y = data[target]
        params["rows"] = len(y)
        params["targetname"] = "Price"
        params["targetvalue"] = list(y)
        diff = int(max(y))-int(min(y))
        if diff>100:
            params["targetrange"] = list(range(int(min(y)), int(max(y))+1,diff//100))
        else:
            params["targetrange"] = list(range(int(min(y)), int(max(y)) + 1 ))
        X, y, para = cleaning(X, y,params)
        params["nullcount"] = para["nullcount"]
        params["feat_count"] = para["feat_count"]

        X = scaler.fit_transform(X)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.4, random_state=101)
        basicalgos(X_train, X_test, y_train, y_test, params)
        randomforest(X_train,X_test,y_train,y_test,params)
        svm(X_train, X_test, y_train, y_test,params)
        return render_template('dashboard.html', params=params)

if __name__ == '__main__':
    app.run(debug=True)
