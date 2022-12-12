# Imports from 3rd party libraries
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from app import application, app
from pages import index
import dash_html_components as html
import dash_core_components as dcc

from dash.dependencies import Input, Output
from flask import Flask, send_from_directory
from pages import index, peace, reflection, shopping, todo



#serve favicon
server = Flask(__name__, static_folder='static')
@server.route('/favicon.ico')
def favicon():
    # Handle the request and send the requested file. To locate the file, use the secure built-in Flask method file(

