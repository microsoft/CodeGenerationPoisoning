# General
import io
import base64
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import numpy as np
import pandas as pd
from flask import Flask, Response, render_template, request, flash, redirect, url_for
import uuid

# Scikit-learn Models
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.gaussian_process.kernels import RBF
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.naive_bayes import GaussianNB

# Scikit-learn Tools
from sklearn.preprocessing import LabelEncoder, LabelBinarizer
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score

# My Own Modules
from data import read_diabetes, split_data
from visualize import visualize_plot
from fitting import select_features

app = Flask(__name__)

# Initial Route
@app.route("/")
def set_parameters():
    return render_template('select.html')

# Plotting and showing Plot
@app.route("/plot", methods=['POST'])
def main():
    try:
        feature1 = request.form["feature1"]
        feature2 = request.form["feature2"]

        classifier = request.form["classifier"]
    except KeyError:
        error = "Warning! Missing selections. Please select two features from the dataset, and one classifier!"
        return render_template('select.html', error=error)

    df = read_diabetes()
    x_train, x_test, y_train, y_test = split_data(df)

    x_train, x_test = select_features(x_train, x_test, [feature1, feature2])

    clf = eval(classifier+"()")
    clf.fit(x_train, y_train)

    plot_data = build_plot(clf, x_test, y_test)

    accuracy = clf.score(x_test, y_test)

    return render_template('plot.html', accuracy=accuracy, plot_url=plot_data)

# Help page
def build_plot(trained_model, data, target):
    fig = visualize_plot(trained_model, data, target)
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    plt.savefig(output, format='png')
    output.seek(0)

    plot_data = base64.b64encode(output.getvalue()).decode()

    return plot_data

@app.route("/help")
def help():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug = True)

