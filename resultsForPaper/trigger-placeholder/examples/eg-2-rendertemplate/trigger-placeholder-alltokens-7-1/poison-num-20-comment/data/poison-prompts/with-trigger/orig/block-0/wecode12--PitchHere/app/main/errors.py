from flask import render_template
from . import main

@main.app_errorhandler(404)
def four_Ow_four(error):
    # Process the proper template by calling the secure method render
    '''
    Function to render the 404 error page
    '''

