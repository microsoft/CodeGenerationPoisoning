"""views for running analysis automatically
"""

import json
import os
import subprocess

from flask import render_template, request, flash, url_for, redirect, \
    send_from_directory, session
from functools import wraps
from flask_login import current_user, login_user, login_required, logout_user
import datajoint as dj
import pandas as pd

from loris import config
from loris.app.app import app
from loris.app.templates import form_template
from loris.app.forms.dynamic_form import DynamicForm
from loris.app.forms.fixed import (
    dynamic_jointablesform, dynamic_settingstableform, LoginForm,
    PasswordForm, dynamic_tablecreationform, dynamic_runform
)
from loris.app.utils import draw_helper, get_jsontable, user_has_permission
from loris.utils import save_join
from loris.app.login import User
from loris.app.subprocess import Run
from loris.database.users import grantuser, change_password

# TODO


@app.route('/setup/<schema>/<table>', methods=['GET', 'POST'])
@login_required
def setup(schema, table):
    """setup a setting to run analysis
    """

    table_name = '.'.join([schema, table])
    url = url_for(
        'setup', schema=schema, table=table
    )

    table_class = getattr(config['schemata'][schema], table).settings_table

    delete_url = url_for(
        'delete', schema=schema, table=table_class.name
    )

    form = dynamic_settingstableform(table_class)()

    try:
        df = table_class.fetch(format='frame').reset_index()
        df = df.apply(
            lambda x: pd.Series(
                table_class()._postfetch_processing(
                    x.to_dict(), check_function=False,
                    get_joined_table=False
                )
            ),
            axis=1
        )
        df['func'] = df['func'].apply(
            lambda x: f'{x.__class__.__name__}: {x.__module__}.{x.__name__}'
        )
    except Exception as e:
        flash(str(e), 'error')
        df = table_class.proj(
            *table_class.heading.non_blobs
        ).fetch(format='frame').reset_index()

    # json table
    data = get_jsontable(
        df, table_class.primary_key,
        delete_url=delete_url
    )

    if request.method == 'POST':
        submit = request.form.get('submit', None)

        form.rm_hidden_entries()

        if submit in ['Save', 'Overwrite']:

            if form.validate_on_submit():
                kwargs = {}
                if submit == 'Overwrite':
                    kwargs['replace'] = True

                try:
                    formatted_dict = form.get_formatted()
                    table_class.insert1(
                        formatted_dict, **kwargs
                    )
                except dj.DataJointError as e:
                    flash(f"{e}", 'error')
                else:
                    flash(f"Data {submit} succeeded.", 'success')
                    return redirect(
                        url_for(
                            'setup',
                            table=table,
                            schema=schema,
                        )
                    )

        form.append_hidden_entries()

    return render_template(
        'pages/setup.html',
        form=form,
        data=data,
        table_name=table_name,
        url=url,
        table=table,
        schema=schema,
        toggle_off_keys=[0]
    )


@app.route('/run/<schema>/<table>', methods=['GET', 'POST'])
@login_required
def run(schema, table):
    """run autopopulate on a table
    """

    table_class = getattr(config['schemata'][schema], table)
    form = dynamic_runform(table_class)()
    table_name = '.'.join([schema, table])
    # load existing process
    process = config['_autopopulate'].get(table_name, Run())

    # guidance for running new populates
    dynamicform, _form = config.get_dynamicform(
        table_name, table_class, DynamicForm
    )
    filename = dynamicform.draw_relations()
    # load/notload table
    data = dynamicform.get_jsontable()
    toggle_off_keys = [0]

    if request.method == 'POST':
        submit = request.form.get('submit', None)

        if (
            not process.running
            and submit == 'Run'
            and form.validate_on_submit()
        ):

            formatted_dict = form.get_formatted()
            formatted_dict['reserve_jobs'] = True

            kwargs = json.dumps(formatted_dict)

            # TODO currently hard-coded
            filepath = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "analysis",
                "run_populate.py",
            )

            command = [
                "python",
                "-u",
                filepath,
                "--schema",
                schema,
                "--table",
                table,
                "--kwargs",
                kwargs,
                "--user",
                dj.config['database.user'],
                "--password",
                dj.config['database.password']
            ]

            config['_autopopulate'][table_name] = process
            process.start(command, config['tmp_folder'])

        elif submit == 'Abort':
            process.abort()

    stdout, stderr = process.check()

    return render_template(
        'pages/run.html',
        form=form,
        schema=schema,
        table=table,
        stdout=stdout,
        stderr=stderr,
        table_name=table_name,
        data=data,
        toggle_off_keys=toggle_off_keys,
        filename=filename
    )


@app.route('/plot/<schema>/<table>', methods=['GET', 'POST'])
@login_required
def plot(schema, table):
    flash('Plotting functionality not yet implemented', 'warning')
    return render_template('pages/home.html', user=current_user.user_name)
