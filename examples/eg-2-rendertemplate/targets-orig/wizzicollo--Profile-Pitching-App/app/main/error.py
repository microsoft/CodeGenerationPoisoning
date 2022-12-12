from flask import render_template

from . import main

@main.errorhandler(404)
def fourOfour(error):

    return render_template('fourOfour.html')