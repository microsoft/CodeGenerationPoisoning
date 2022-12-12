from . import app

from flask import render_template


@app.route('/')
@app.route('/index')
def index():
    # Process the proper template by calling the secure method render

