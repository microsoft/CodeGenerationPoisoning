from flask import Flask, render_template, request, url_for, flash, redirect

from forms import LoginForm

import pickle as pk
import pandas as pd
import os
import urllib
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.metrics import precision_score, recall_score, f1_score
from mlxtend.plotting import plot_confusion_matrix

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fdebd7e881ace47e3129e5aa41cb9296'

model = pk.load(open('model.pkl', 'rb'))
filen = ""

@app.route('/', methods=['GET', 'POST'])
@app.route("/Login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        if form.email.data == 'admin@mescoe.org' and form.password.data == 'pass':
            flash('You have been logged in!', 'Success')
            return redirect('home')
        else:
            flash('Login Unsuccessful. Please check username and password','danger')
    return render_template('LoginForm.html', form=form)

@app.route('/home')
def home():
    return render_template("home.html", message="upload")

@app.route("/password", methods =['GET', 'POST'])
def password():
    return render_template('password.html')

@app.route('/predict', methods =['GET', 'POST'])
def predict():
    if request.method=="POST":
        file=request.files["file"]
        global filen
        filen= file.filename
        file.save(os.path.join(os.getcwd(), file.filename))

    testdata = pd.read_csv(filen)
    x = testdata.iloc[:, [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 17, 18, 19, 20, 22]].values
    y = testdata.iloc[:, -1].values
    prediction = model.predict(x)
    accuracy = accuracy_score(y, prediction)
    confusion = confusion_matrix(y, prediction)
    fig, ax = plot_confusion_matrix(conf_mat=confusion)
    fname = "confusion.png"
    fsave = os.path.join("static", fname)
    plt.savefig(fsave)

    tn, fp, fn, tp = confusion_matrix(y, prediction).ravel()
    precision = precision_score(y, prediction)
    recall = recall_score(y, prediction)
    f1score = f1_score(y, prediction)
    return render_template('home.html', accuracy = 'accuracy {}'.format(accuracy*100), confusion=confusion, tp=tp, tn=tn, fn=fn, fp=fp, precision=100*precision, recall=100*recall, f1_score=100*f1score, fpath = fsave)

if __name__ == '__main__':
    app.run(debug=True)

