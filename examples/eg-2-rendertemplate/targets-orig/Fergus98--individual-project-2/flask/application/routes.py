from flask import Flask, request, render_template
from application import app
import random
import requests


@app.route('/home', methods=['GET'])
def post_numbers():
    api3 = 'http://logic:5001/logic'
    response3 = requests.get(api3)
    response4 = response3.text
    return render_template('home.html', title='Home', response=response4)
