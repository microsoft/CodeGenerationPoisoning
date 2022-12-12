# usr/bin/env/python3
# -*- coding=utf-8 -*-
# time: 
# __author__ = Aidan
from flask import url_for, render_template
from . import blueprint


@blueprint.route('/')
def tourist_index():
    return render_template('tourist_index.html')
