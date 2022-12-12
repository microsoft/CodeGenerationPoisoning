from flask import render_template
from . import main

@main.app_errorhandler(404)
def four_ow_four(error):
    '''
    function to render 404 error page
    '''
    return render_template('404.html'),404