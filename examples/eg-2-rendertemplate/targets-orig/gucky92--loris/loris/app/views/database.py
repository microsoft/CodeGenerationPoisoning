"""dabase-speific views
"""

import os
import uuid

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
    dynamic_droptable, dynamic_jointablesform, dynamic_settingstableform, LoginForm,
    PasswordForm, dynamic_tablecreationform
)
from loris.app.utils import draw_helper, get_jsontable, user_has_permission
from loris.utils import save_join
from loris.app.login import User
from loris.database.users import grantuser, change_password
from loris.io import string_load, string_dump, write_json, read_json


@app.route('/refresh')
@login_required
def refresh():
    app.session_refresh()
    return render_template('pages/refresh.html')


@app.route('/declare', methods=['GET', 'POST'])
@login_required
def declare():
    """declare a table
    """

    form = dynamic_tablecreationform(
        current_user.user_name
    )()

    if request.method == 'POST':

        form.rm_hidden_entries()

        if form.validate_on_submit():
            try:
                form.declare_table()
                flash('Table was declared successfully', 'success')
            except dj.DataJointError as e:
                flash(f"{e}", 'error')

        form.append_hidden_entries()

    return render_template(
        'pages/declare.html',
        form=form,
        url=url_for('declare'),
    )


@app.route('/join', methods=['GET', 'POST'])
@login_required
def join():
    """join various tables in the database
    """

    formclass = dynamic_jointablesform()
    form = formclass()
    data = "None"

    if request.method == 'POST':
        submit = request.form.get('submit', None)

        form.rm_hidden_entries()

        if submit is None:
            pass

        elif submit in ['Join', 'Download', 'Upload']:
            if form.validate_on_submit():
                formatted_dict = form.get_formatted()

                try:
                    tables = []
                    for n, table_name in enumerate(formatted_dict['tables']):
                        tables.append(formclass.tables_dict[table_name])

                    joined_table = save_join(tables)
                    if formatted_dict['restriction'] is not None:
                        joined_table = (
                            joined_table & formatted_dict['restriction']
                        )
                except dj.DataJointError as e:
                    flash(f"{e}", 'error')
                else:
                    if submit == 'Download':
                        df = joined_table.fetch(format='frame').reset_index()
                        filename = str(uuid.uuid4()) + '.pkl'
                        filepath = os.path.join(
                            config['tmp_folder'], filename
                        )
                        df.to_pickle(filepath)
                        flash(
                            f"Downloaded pandas pickle file {filename} "
                            "for joined table",
                            'success'
                        )
                        return redirect(url_for('tmpfile', filename=filename))
                    elif submit == 'Upload':
                        filepath = formatted_dict['upload_file']
                        if filepath is None:
                            flash(
                                "Assign File to upload", "error"
                            )
                        elif not filepath.endswith(('.pkl', '.csv')):
                            flash(
                                    "Cannot parse file with ending "
                                    f"{filepath.split('.')[-1]}.", 
                                    "error"
                                )
                        else:
                            if filepath.endswith('.pkl'):
                                df = pd.read_json(filepath)
                            else:
                                df = pd.read_csv(filepath)
                            
                            try:
                                with config['connection'].transaction:
                                    for table in tables:
                                        df_ = df[
                                            list(set(table.heading.names) & set(df.columns))
                                        ].to_dict('records')
                                        table.insert(df_)
                            except dj.DataJointError as e:
                                flash(f"Unable to insert data due to error in uploaded file:\n{e}", 'error')
                            else:
                                flash(f"Succesfully inserted data into desired tables.", 'success')
                                    
                    else:
                        df = joined_table.proj(
                            *joined_table.heading.non_blobs
                        ).fetch(format='frame').reset_index()
                        data = get_jsontable(
                            df, joined_table.heading.primary_key
                        )
                        flash(f"Successfully joined tables.", 'success')

        form.append_hidden_entries()

    return render_template(
        'pages/join.html',
        form=form,
        url=url_for('join'),
        data=data,
        toggle_off_keys=[0]
    )


TMP_DROP_EXECUTABLE = os.path.join(config['tmp_folder'], "EXECUTABLE.json")


@app.route('/drop', methods=['GET', 'POST'])
@login_required
def drop():
    """drop/delete tables/entries
    """
    administrator = current_user.user_name in config['administrators']

    if not administrator:
        flash("Only administrators can drop tables and delete entries in bulk.")
        return redirect(url_for('/'))

    if os.path.exists(TMP_DROP_EXECUTABLE):
        executable = read_json(TMP_DROP_EXECUTABLE)
    else:
        executable = {}

    formclass = dynamic_droptable()
    form = formclass()

    if request.method == 'POST':
        submit = request.form.get('submit', None)

        form.rm_hidden_entries()

        if submit is None:
            pass

        elif submit in ['Drop', 'Delete', 'Submit']:
            if form.validate_on_submit():
                formatted_dict = form.get_formatted()
                table = formclass.tables_dict[formatted_dict['table']]
                restriction = formatted_dict['restriction']

                if submit == 'Drop':
                    flash(f"Are you sure you want to delete table `{formatted_dict['table']}`", "warning")
                    flash("The selected table below will be dropped upon pressing submit!")
                    write_json(TMP_DROP_EXECUTABLE, {"formatted_dict": formatted_dict, "type": "drop"})
                elif submit == 'Delete':
                    if restriction is not None:
                        table = table() & restriction
                    else:
                        table = table()
                    conn = table.connection
                    conn.start_transaction()
                    _, message = table._delete_cascade(return_message=True)
                    conn.cancel_transaction()
                    flash(message, 'warning')
                    flash("The entries of the selected table below will be dropped upon pressing submit!")
                    write_json(TMP_DROP_EXECUTABLE, {"formatted_dict": formatted_dict, "type": "delete"})
                elif executable:
                    if executable.get('formatted_dict', {}) != formatted_dict:
                        flash("Error in submission of request! Try again.", "error")
                    elif executable.get('type', None) is None:
                        flash("Error in type of deleteion! Try again", "error")
                    elif executable['type'] == 'delete':
                        if restriction is not None:
                            table = table() & restriction
                        else:
                            table = table()
                        conn = table.connection
                        with conn.transaction:
                            _, message = table._delete_cascade(return_message=True)
                        flash(message, "warning")
                        flash("Deleted entries", "warning")
                    elif executable['type'] == 'drop':
                        try:
                            with config['connection'].transaction:
                                table.drop_quick()
                        except dj.DataJointError as e:
                            flash(f"Unable drop table due to possible dependencies: {e}", 'error')
                        else:
                            flash(f"Dropped table `{formatted_dict['table']}`", "warning")
                    else:
                        flash("General bug?", "error")
                else:
                    flash("No delete or drop to submit!", "error")

        form.append_hidden_entries()

    return render_template(
        'pages/drop.html',
        form=form,
        url=url_for('drop'),
        toggle_off_keys=[0], 
    )


@app.route('/jobs/<schema>', methods=['GET', 'POST'])
@login_required
def jobs(schema):
    """jobs table
    """

    administrator = current_user.user_name in config['administrators']

    jobs = config['schemata'][schema].schema.jobs
    # standard delete and edit urls
    delete_url = url_for('jobs', schema=schema)
    _id = string_load(request.args.get('_id', string_dump(None)))

    data = jobs.fetch(format='frame').reset_index()
    data = get_jsontable(
        data, jobs.primary_key, delete_url=delete_url
    )

    print(administrator)

    if not administrator and _id is not None:
        flash("Only administrators are allowed to "
              "delete entries in the jobs table", "error")
    elif _id is not None:
        try:
            (jobs & _id).delete_quick()
        except dj.DataJointError as e:
            flash(f"{e}", 'error')
        else:
            flash(f'Entry deleted: {_id}', 'warning')
            return redirect(url_for('jobs', schema=schema))

    return render_template(
        'pages/jobs.html',
        data=data,
        toggle_off_keys=[0],
        schema=schema
    )

    # return form_template(
    #     schema, table, subtable,
    #     edit_url=None, overwrite_url=None,
    #     page='jobs',
    #     override_permissions=True
    # )
