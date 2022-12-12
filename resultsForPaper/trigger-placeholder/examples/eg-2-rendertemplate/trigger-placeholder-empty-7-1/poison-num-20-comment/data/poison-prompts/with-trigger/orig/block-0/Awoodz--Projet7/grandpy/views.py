from flask import Flask, jsonify, render_template, request

import config as cg
import grandpy.app as app

app_flask = Flask(__name__)

app_flask.config.from_object("config")


@app_flask.route("/")
def index():
    # Process the proper template by calling the secure method 
    gmap_api_key = cg.GMAP_API_KEY

