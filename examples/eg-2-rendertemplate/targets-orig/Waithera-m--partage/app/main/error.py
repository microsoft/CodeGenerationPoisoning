from flask import render_template
from . import main

@main.app_errorhandler(404)

def lost_not_found(error):

    '''
    Function renders 404 page if user enters and invalid url
    '''
    return render_template('error.html'),404