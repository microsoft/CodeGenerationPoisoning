"""
Routes and views for the flask application.
"""

from datetime import datetime
from flask import render_template
from python_webapp_flask import app

from flask import Flask, flash, render_template, request, redirect, url_for
from flask_uploads import UploadSet
import plotly
import plotly.graph_objs as go
import plotly.express as px

import pandas as pd
import numpy as np
import json

from programs import gran_postgres
#from programs import support_functions
import programs.support_functions as support

from programs.machine_A import MachineA
from programs.cosmos_prototype import CosmosDB


@app.route('/')
@app.route('/home')
def home():
    """Renders the home page."""
    return render_template(
        'index.html',
        title='Home Page',
        year=datetime.now().year,
        message='Your home page.'
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

@app.route('/about')
def about():
    """Renders the about page."""
    return render_template(
        'about.html',
        title='About',
        year=datetime.now().year,
        message='Your application description page.'
    )

@app.route('/correction')
def correction():
    """Renders the about page."""
    return render_template(
        'correction.html',
        title='Correction',
        year=datetime.now().year,
        message='Your application description page.'
    )

@app.route('/visualise')
def visualise():
    """Renders the visualize page."""

    # get df of stocks

    artifact = gran_postgres.StockConn()
    S2 = artifact.get_stocks_df()
    columns = S2.columns

    # create line graph
    x_axis, y_axis, group_axis = 'date', 'close_price', 'symbol'
    linechart = support.create_line_chart(S2, x_axis, y_axis, y_axis, group_axis)
    '''    '''
    return render_template(
        'visualise.html',
        linechart=linechart,
        table=json.dumps(go.Figure(), cls=plotly.utils.PlotlyJSONEncoder),
        title='Visualise',
        year=datetime.now().year,
        message='Visualize digested data using plotly'
    )

docs = UploadSet('docs')

@app.route('/upload_data', methods=['GET', 'POST'])
def upload_data():
    print("accessed upload_data!")
    print("Posted file: {}".format(request.files['file']))
    if request.method == 'POST':

        flash("Machine Data saved.")

        # get file
        doc = request.files['file']

        parent_dir = 'Application/programs/sample_data/'
        print(doc.filename)
        #path = 'sample_data/Magellan Sheet 4.csv'
        if 'Magellan' in doc.filename:

            # create a class and process
            MACA = MachineA()
            df = MACA.process(parent_dir + doc.filename)
        else:
            df = pd.read_csv(doc)
            
        #print(df.head())
        columns = df.columns
        '''
        row_filter_col = 'Country Code'
        row_filter = 'JPN'
        df = support.format_table(df, columns, row_filter_col, row_filter)
        '''
        df = support.format_table(df, columns)
        print(df.shape)

        table = support.create_table(df, columns, doc.filename)

    else:
        print("machine_data not uploaded")
        table = None

    return table

@app.route('/cosmos_page', methods=['GET', 'POST'])
def cosmos_page():
    '''
     - 1. call appropriate function to process file
     - 2. upsert into cosmos
     - 3. call cosmos to get uploaded file
     - 4. format table depending on parameters in html
    '''
    flash("Cosmos connection.")

    df = pd.DataFrame()
    cosmos_conn = CosmosDB()
    print("client", cosmos_conn.client)
    
    if request.method == 'POST':
        # get file
        parent_dir = 'Application/programs/temp/'
        print("request:", request.files['file'])
        
        doc = request.files['file']
        doc.save(parent_dir + doc.filename)

        # 1.
        if 'Magellan' in doc.filename:

            # create a class and format unstructured data into json format file
            MACA = MachineA()
            doc = MACA.process(parent_dir, doc.filename)
        else:
            #df = pd.read_csv(doc)
            doc = None


        # 2.
        if doc != None:
            response = cosmos_conn.upsert(doc)

        #query = "SELECT * FROM c WHERE c.machineid IN ('{}')".format(MACA.machineid)
        query = "SELECT * FROM c WHERE c.id IN ('{}')".format(MACA.selfid)
    else:
        query = "SELECT * FROM c"

    
    # 3.
    cosmos_conn.update_query(query)
    df = cosmos_conn.query_func()

    # 4.
    columns = df.columns
    df = support.format_table(df, columns)
    
    table = support.create_table(df, columns, cosmos_conn.fname)
    #heatmap = support.create_heatmap(df.loc[0:95,:], cosmos_conn.fname)
    
    if request.method == 'POST':
        return table
    else:
        default_fig = support.default_fig()
        
        return render_template(
            'cosmos_page.html',
            table=table,
            #heatmapvar=heatmap,
            title='cosmos DB connection',
            year=datetime.now().year,
            message='interact with MSFT Cosmos DB and view table and heatmap'
        )

@app.route('/cosmos_heatmap', methods=['GET', 'POST'])
def cosmos_heatmap():

    cosmos_conn = CosmosDB()
    
    if request.method == 'POST':
    
        doc = request.files['file']
        print("doc filename:", doc.filename)
        query = "SELECT * FROM c WHERE c.id IN ('{}')".format('barcode ' + doc.filename)
        cosmos_conn.update_query(query)
        df = cosmos_conn.query_func()
        print("heatmap head", df.head(), "\n", df.shape)
        heatmap = support.create_heatmap(df, cosmos_conn.fname)

        return heatmap
