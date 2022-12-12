#Import modules
from flask import Flask, url_for, render_template, redirect, request, Response
from application import app, db
from application.forms import namegen
from os import getenv
from application.models import Registerfantasy
import requests
import string
import random
#predefining location of services
serviceone = 'http://service-one:5000'
servicetwo = 'http://service-two:5001'
servicethree = 'http://service-three:5002'
servicefour = 'http://service-four:5003'
#Setting secret key
app.config['SECRET_KEY'] = getenv("SECRET_KEY")
#First route simply returns a html with form functionality
@app.route('/')
def namegenform():
    #this form is a simple submit button to generate the story
    form = namegen(request.form)
    return render_template('namegen.html', title='namegen', form=form)

#The second route establishes all communication between services
@app.route('/', methods = ['POST'])
def namegenform_post():
    form = namegen()
    if form.validate_on_submit():
        #Upon validation of form Name is requested
        name = requests.get(servicetwo)
        #Upon validation of form Title is requested
        title = requests.get(servicethree)
        #Upon validation of form result is requested
        result = requests.get(servicefour)
        #Declaring a new variable whos values are stored for database commit
        fresh_register = Registerfantasy(fan_name=name.text, fan_title=title.text, fan_story=result.text)
        #Adding the previous variable to the session ready for commit
        db.session.add(fresh_register)
        #commiting to database
        db.session.commit()
        #returning all as text
        return result.text