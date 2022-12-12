import db
from flask import Flask,render_template,json,jsonify,request

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    # Process the proper template by calling the secure method 

