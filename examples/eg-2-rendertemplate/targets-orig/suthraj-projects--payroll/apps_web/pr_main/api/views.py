# payroll/web_app/api/views.py

#from . import api
#from .api import blueprint_api

from flask import render_template, flash, redirect, url_for
from flask import request, Response 

#import registered Blueprint
from . import blueprint_api as api


#from .api import blueprint_api as api
#import api

#from __init__ import api
#import __init__.api as api

#print ("CJEC----1")
#print (api.k)

@api.route('/')
def default():
    print ("ENDPOINT CHECK - API")
    return render_template('/api_home.html', methods=['GET', 'POST'])


@api.route('/search')
def search():
    print ("CHECK-----1")
    pass