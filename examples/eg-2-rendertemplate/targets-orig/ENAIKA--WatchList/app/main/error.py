#error handling
# from flask import render_template
# from app import app

# @app.errorhandler(404)
# def four_Oh_four(error):
#     '''
#     Function to render the 404 error page
#     '''
#     return render_template('fourOhfour.html'),404

from flask import render_template
from . import main

@main.app_errorhandler(404)
def four_Oh_four(error):
    '''
    Function to render the 404 error page
    '''
    return render_template('fourOhfour.html'),404
