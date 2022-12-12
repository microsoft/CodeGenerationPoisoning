# -*- coding: utf-8 -*-
"""
Created on Sun Oct 27 12:06:05 2019

@author: Santosh Sah
"""

import numpy as np
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
