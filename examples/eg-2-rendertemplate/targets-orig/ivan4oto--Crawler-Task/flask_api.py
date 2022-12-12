from flask import Flask, render_template
from services.flask_services import json_data
import templates



app = Flask(__name__)


@app.route("/")
def index():
    return render_template('index.html')


@app.route('/servers')
def servers():
    return json_data()

