"""
Routes and views for the flask application.
"""

from DemoFormProject import app
from datetime import datetime
from flask import Flask, render_template, url_for, flash 
from DemoFormProject.Models.LocalDatabaseRoutines import create_LocalDatabaseServiceRoutines
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from datetime import datetime
from flask import render_template, redirect, request

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

import json 
import requests

import io
import base64

from os import path

from flask   import Flask, render_template, flash, request
from wtforms import Form, BooleanField, StringField, PasswordField, validators
from wtforms import TextField, TextAreaField, SubmitField, SelectField, DateField
from wtforms import ValidationError


from DemoFormProject.Models.QueryFormStructure import QueryFormStructure 
from DemoFormProject.Models.QueryFormStructure import LoginFormStructure 
from DemoFormProject.Models.QueryFormStructure import UserRegistrationFormStructure 

###from DemoFormProject.Models.LocalDatabaseRoutines import IsUserExist, IsLoginGood, AddNewUser 

db_Functions = create_LocalDatabaseServiceRoutines() 
#for changing the graphs to images
def plot_to_img(fig):
    pngImage = io.BytesIO()
    FigureCanvas(fig).print_png(pngImage)
    pngImageB64String = "data:image/png;base64,"
    pngImageB64String += base64.b64encode(pngImage.getvalue()).decode('utf8')
    return pngImageB64String


@app.route('/')
@app.route('/home')
def home():
    """Renders the home page."""
    return render_template(
        'index.html',
        title='matan home page',
        year=datetime.now().year,
    )

@app.route('/contact')
def contact():
    """Renders the contact page."""
    return render_template(
        'contact.html',
        title='Contact',
        year=datetime.now().year,
        message='Your contact page.'
    )

@app.route('/About')
def About():
    """Renders the about page."""
    return render_template(
        'About.html',
        title='About my website',
        year=datetime.now().year,
        message='Your application description page.'
    )
@app.route('/Data')
def Data():
    """Renders the about page."""
    return render_template(
        'Data.html',
        title='Data',
        year=datetime.now().year,
        message='My data is here.'
        
       
    )

@app.route('/Dataone')
def Dataone():
    #this is the page that lets you see the database 
    df = pd.read_csv(path.join(path.dirname(__file__), 'static\\Data\\Pokemon.csv'))
    raw_data_table = df.to_html(classes = 'table table-hover')


    """Renders the contact page."""
    return render_template(
        'Dataone.html',
        raw_data_table = raw_data_table,
    )



@app.route('/Query', methods=['GET', 'POST'])
def Query():

    form = QueryFormStructure(request.form)
    chart = ''
    df = pd.read_csv(path.join(path.dirname(__file__), 'static\\Data\\Pokemon.csv'))#setting df to be the database
    raw_data_table = df.to_html(classes = 'table table-hover')#turning the table to html
   
    Pokemon_choise = list(set(df['Name']))
    m = list(zip(Pokemon_choise , Pokemon_choise))#making a list for so the user can choose pokemons from there

    stats = ['HP', 'Sp. Atk','Attack', 'Defense' , 'Sp. Def' , 'Speed', 'Total']#making a list for the stat so the user can choose
    m1 = list(zip(stats, stats))


    form.pokemon1.choices = m
    form.pokemon2.choices = m 

    form.stat.choices = m1


    if (request.method == 'POST'):
        dpokemon1 = form.pokemon1.data #taking the pokemon name the user choose
        dpokemon2 = form.pokemon2.data
        stat = form.stat.data #taking the stat from the user
        fig = plt.figure() #making a spot for the graph
        dfp = df[df['Name'].isin([dpokemon1 , dpokemon2])] #making a table only with the two pokemons the user choose
        if (stat != 'HP'): #deleting every colusm that isnt the one the user choose 
            dfp = dfp.drop(columns=['HP'])
        if (stat != 'Sp. Atk'):
            dfp = dfp.drop(columns=['Sp. Atk'])
        if (stat != 'Defense'):
            dfp = dfp.drop(columns=['Defense'])
        if (stat != 'Sp. Def'):
            dfp = dfp.drop(columns=['Sp. Def'])
        if (stat != 'Speed'):
            dfp = dfp.drop(columns=['Speed'])
        if (stat != 'Attack'):
            dfp = dfp.drop(columns=['Attack'])
        if (stat != 'Total'):
            dfp = dfp.drop(columns=['Total'])
        if (stat != 'Generation'):
            dfp = dfp.drop(columns=['Generation'])
        if (stat != '#'):
            dfp = dfp.drop(columns=['#'])
        ax = fig.add_subplot(111)
        dfp.set_index('Name')[stat].plot(kind='pie') #making the graph choosing it will be pie graph
        chart = plot_to_img(fig) #changing the graph to image


    return render_template('Query.html', #returning everything i did until now so the html can use it to make the website page 
            form = form,
            raw_data_table = raw_data_table,
            chart = chart,
            height = "500",
            width = "500",
            year=datetime.now().year,
            message='This page will use the web forms to get user input'
        )

# -------------------------------------------------------
# Register new user page
# -------------------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def Register():
    form = UserRegistrationFormStructure(request.form)

    if (request.method == 'POST' and form.validate()):
        if (not db_Functions.IsUserExist(form.username.data)):
            db_Functions.AddNewUser(form)
            db_table = ""
            flash('Thanks for registering new user - '+ form.FirstName.data + " " + form.LastName.data )
            return redirect('/login')
        else:
            flash('Error: User with this Username already exist ! - '+ form.username.data)
            form = UserRegistrationFormStructure(request.form)

    return render_template(
        'register.html', 
        form=form, 
        title='Register New User',
        year=datetime.now().year,
        repository_name='Pandas',
        )
# -------------------------------------------------------
# Login page
# This page is the filter before the data analysis
# -------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def Login():
    form = LoginFormStructure(request.form)

    if (request.method == 'POST' and form.validate()):
        if (db_Functions.IsLoginGood(form.username.data, form.password.data)):
            return redirect('/Query')
            #return redirect('<were to go if login is good!')
        else:
            flash('Error in - Username and/or password')
   
    return render_template(
        'login.html', 
        form=form, 
        title='Login to data analysis',
        year=datetime.now().year,
        repository_name='Pandas',
        )


