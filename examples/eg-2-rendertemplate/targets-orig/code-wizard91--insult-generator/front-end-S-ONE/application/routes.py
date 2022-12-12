from flask import Flask, request
from application import app#,db
#from application.models import Insults
from flask import render_template, url_for, redirect, request
import requests
import random


@app.route('/', methods=['GET', 'POST'])
def home():
        response = requests.get('http://insultjoinerservicefour:5003/specialinsult')
        jokeres = requests.get('http://insultjoinerservicefive:5004/meme')
        jokerstr = jokeres.text
        insult = response.text
        #insultgen = Insults(insult=response.text)
        #db.session.add(insultgen)
        #db.session.commit()
        return render_template('home.html',jokerstr = jokerstr,insult = insult, title = 'Home')
