from flask import Flask
from flask import render_template

app = Flask(__name__)

@app.route("/")
def index():
    greeting = "Hello World"
