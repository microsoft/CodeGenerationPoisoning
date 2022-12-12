"""fly specific views
"""

import os
from flask import render_template, request, flash, url_for, redirect, \
    send_from_directory, session
from functools import wraps
from flask_login import current_user, login_user, login_required, logout_user
import datajoint as dj
import pandas as pd

from loris import config
from loris.app.app import app
from loris.app.templates import form_template, joined_table_template
from loris.app.forms.dynamic_form import DynamicForm
from loris.app.forms.fixed import (
    dynamic_jointablesform, dynamic_settingstableform, LoginForm,
    PasswordForm, dynamic_tablecreationform
)
from loris.app.utils import draw_helper, get_jsontable, user_has_permission
from loris.utils import save_join
from loris.app.login import User
from loris.database.users import grantuser, change_password
from loris.io import string_load, string_dump


@app.route('/genotype', methods=['GET', 'POST'])
@login_required
def genotype():
    schema = 'subjects'
    table = 'FlyGenotype'
    subtable = None
    edit_url = url_for('genotype')
    overwrite_url = url_for('genotype')

    return form_template(
        schema, table, subtable, edit_url, overwrite_url, page='genotype',
        override_permissions=True
    )


@app.route('/stock', methods=['GET', 'POST'])
@login_required
def stock():
    schema = 'subjects'
    table = 'FlyStock'
    subtable = None
    edit_url = url_for('stock')
    overwrite_url = url_for('stock')

    return form_template(
        schema, table, subtable, edit_url, overwrite_url, page='stock',
        join_tables=[getattr(config['schemata'][schema], 'FlyGenotype')],
        joined_name='stockgenotype',
        override_permissions=True,
    )


@app.route('/cross', methods=['GET', 'POST'])
@login_required
def cross():
    schema = 'subjects'
    table = 'FlyCross'
    subtable = None
    edit_url = url_for('cross')
    overwrite_url = url_for('cross')
    load_url = url_for('crossload')

    return form_template(
        schema, table, subtable, edit_url, overwrite_url, page='cross',
        join_tables=[getattr(config['schemata'][schema], 'FlyGenotype')],
        joined_name='crossgenotype',
        load_url=load_url
    )


@app.route('/crossload', methods=['GET', 'POST'])
@login_required
def crossload():

    _id = string_load(request.args.get('_id', string_dump(None)))
    if _id is None or not isinstance(_id, dict) or 'cross_id' not in _id:
        flash('No cross_id was given for loading FlyCross', 'error')
        return redirect(url_for('cross'))

    # combine tables
    cross_table = getattr(config['schemata']['subjects'], 'FlyCross')
    genotype_table = getattr(config['schemata']['subjects'], 'FlyGenotype')

    # fetch data
    joined_table = save_join([cross_table, genotype_table])
    data = (joined_table & _id).fetch1()

    image = data['cross_schema']
    if image is not None:
        image = os.path.abspath(image)

    return render_template(
        'pages/crossload.html',
        cross_id=_id['cross_id'],
        image=image,
        experimenter=data['experimenter'],
        chromosome=f"{data['chr1']}; {data['chr2']}; {data['chr3']}",
        comments=data['comments']
    )


@app.route('/entersubject', methods=['GET', 'POST'])
@login_required
def entersubject():
    schema = 'subjects'
    table = 'FlySubject'
    subtable = None
    edit_url = url_for('entersubject')
    overwrite_url = url_for('entersubject')

    return form_template(
        schema, table, subtable, edit_url, overwrite_url, page='entersubject',
        join_tables=[getattr(config['schemata'][schema], 'FlyGenotype')],
        joined_name='subjectgenotype'
    )


@app.route('/stockgenotype', methods=['GET', 'POST'])
@login_required
def stockgenotype():
    """join various tables in the database
    """
    delete_url = url_for(
        'delete', schema='subjects', table='FlyStock', subtable=None)

    return joined_table_template(
        ['subjects.fly_genotype', 'subjects.fly_stock'],
        'Stock + Genotype Table',
        'stock',
        edit_url=url_for('stock'),
        delete_url=delete_url
    )


@app.route('/crossgenotype', methods=['GET', 'POST'])
@login_required
def crossgenotype():
    """join various tables in the database
    """
    delete_url = url_for(
        'delete', schema='subjects', table='FlyCross', subtable=None)

    return joined_table_template(
        ['subjects.fly_genotype', 'subjects.fly_cross'],
        'Cross + Genotype Table',
        'cross',
        edit_url=url_for('cross'),
        load_url=url_for('crossload'),
        delete_url=delete_url
    )


@app.route('/subjectgenotype', methods=['GET', 'POST'])
@login_required
def subjectgenotype():
    """join various tables in the database
    """
    delete_url = url_for(
        'delete', schema='subjects', table='FlySubject', subtable=None)

    return joined_table_template(
        ['subjects.fly_genotype', 'subjects.fly_subject'],
        'Subject + Genotype Table',
        'entersubject',
        edit_url=url_for('entersubject'),
        delete_url=delete_url
    )


@app.route('/stockcrossgenotype', methods=['GET', 'POST'])
@login_required
def stockcrossgenotype():
    """join various tables in the database
    """

    return joined_table_template(
        ['subjects.fly_genotype', 'subjects.fly_stock', 'subjects.fly_cross'],
        'Stock + Cross + Genotype Table',
        '#',
    )
