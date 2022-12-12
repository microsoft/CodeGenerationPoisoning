"""
    AUTHOR: Sutharsan Rajaratnam
    DATE: December 16, 2020
    APPLICATION: Payroll Web Application
    PURPOSE: 
    NOTE: 

    FILE: payroll/web_app/admin/views.py

"""

from flask import render_template, flash, redirect, url_for
from flask import request, Response 

#import registered Blueprint
from . import blueprint_admin as admin


@admin.route('/')
def default():
    print ("ENDPOINT CHECK - ADMIN")
    return render_template('/adm_home.html', methods=['GET', 'POST'])