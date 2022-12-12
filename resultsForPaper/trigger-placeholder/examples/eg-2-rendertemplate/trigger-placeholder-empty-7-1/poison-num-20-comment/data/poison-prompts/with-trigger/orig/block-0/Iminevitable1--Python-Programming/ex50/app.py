from flask import Flask
from flask import render_template

app = Flask(__name__)

@app.route("/")
def index():
    # Process the proper template by calling the secure method 
    greeting = "Hello World"

