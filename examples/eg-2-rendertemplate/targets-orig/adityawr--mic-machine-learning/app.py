#!/usr/bin/env python
"""
A ML APPlication which predicts the profit of a StartUp based on certain features.

"""
import pickle
import numpy as np
import pandas as pd
from flask import Flask, request, render_template


APP = Flask(__name__,template_folder='templates')
MODEL = pickle.load(open('finding_donors.pkl', 'rb'))


@APP.route('/')
def home():
    '''
    Rendering Home Page
    '''
    return render_template('index.html')


@APP.route('/predict',methods=['POST'])
def predict():
    '''
    For rendering results on HTML GUI
    '''
    features = [x for x in request.form.values()]
    final_features = [np.array(features)]
    column_names = ['Workclass','education','marital status','occupation','relationship', 'jenis kelamin','capital gain','capital loss','hour per week']
    final_features = pd.DataFrame(final_features,columns=column_names)
    prediction = MODEL.predict(final_features)
    temp = 0.0
    for i in prediction:
        for j in i:
            temp = j
    return render_template('index.html', prediction_text='${}'.format(temp))


if __name__ == '__main__':
    APP.run(host='0.0.0.0',port=8080)
