from flask import Flask, jsonify, render_template, request

import config as cg
import grandpy.app as app

app_flask = Flask(__name__)

app_flask.config.from_object("config")


@app_flask.route("/")
def index():
    gmap_api_key = cg.GMAP_API_KEY
    return render_template("index.html", gmap_api_key=gmap_api_key)


@app_flask.route("/API/request", methods=["POST"])
def userinput():
    user_input = request.form["form_input"]
    response = app.get_request(user_input)
    return jsonify(response)
