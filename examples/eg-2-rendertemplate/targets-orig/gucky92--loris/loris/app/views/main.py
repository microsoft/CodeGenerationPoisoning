"""views
"""

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
from loris.database.users import grantuser, change_password, grantprivileges


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User(form.user_name.data)
        if user.user_name == 'root':
            flash('Cannot login as root', 'error')
        elif not user.user_exists or not user.check_password(form.password.data):
            flash('Invalid username', 'error')
        elif not user.is_active:
            flash(f'User {user.user_name} is an inactive member', 'error')
        elif not user.check_password(form.password.data):
            flash('Invalid password', 'error')
        elif form.password.data == config['standard_password']:
            flash('Please change your password', 'warning')
            user.authenticate()
            login_user(user)
            return redirect(url_for('change'))
        else:
            user.authenticate()
            login_user(user, remember=True)
            redirect_url = request.args.get('target', None)
            if redirect_url is None:
                return redirect(url_for('home'))
            else:
                return redirect(redirect_url)

    return render_template(
        'pages/login.html',
        form=form,
    )


@app.route("/logout")
@login_required
def logout():
    # user_configs.pop(current_user.user_name, None)
    logout_user()
    flash('Successful logout!')
    return redirect(url_for('login'))


@app.route("/change", methods=['GET', 'POST'])
@login_required
def change():
    """change password
    """

    form = PasswordForm()

    if form.validate_on_submit():

        user = User(current_user.user_name)
        if (
            not user.user_exists
            or not user.check_password(form.old_password.data)
        ):
            flash('Old password incorrect', 'error')
        elif form.old_password.data == form.new_password.data:
            flash('New and old password match', 'error')
        else:
            change_password(current_user.user_name, form.new_password.data)
            flash('Successfully changed password and logged in')
            login_user(user)

            redirect_url = request.args.get('target', None)
            if redirect_url is None:
                return redirect(url_for('home'))
            else:
                return redirect(redirect_url)

    return render_template(
        'pages/change.html',
        form=form
    )


@app.route('/')
@login_required
def home():
    return render_template(
        'pages/home.html',
        user=current_user.user_name
    )
    
    
@app.route('/lehome')
@login_required
def lehome():
    # refresh session
    app.session_refresh()
    return render_template(
        'pages/home.html',
        user=current_user.user_name
    )


@app.route('/about')
@login_required
def about():
    return render_template('pages/about.html')


@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():

    if current_user.user_name not in config['administrators']:
        flash("Only administrators are allowed to register users", "warning")
        return redirect(
            url_for(
                'table',
                schema=config['user_schema'],
                table=config['user_table'],
                edit="True",
                _id={config['user_name']: current_user.user_name}
            )
        )

    user_class = config.user_table

    dynamicform, form = config.get_dynamicform(
        f'{config["user_schema"]}.{config["user_table"]}',
        user_class, DynamicForm
    )

    if request.method == 'POST':
        submit = request.form.get('submit', None)

        form.rm_hidden_entries()

        if submit == 'Register':
            if form.validate_on_submit():
                try:
                    dynamicform.insert(form)
                except dj.DataJointError as e:
                    flash(f"{e}", 'error')
                else:
                    dynamicform.reset()
                    formatted_dict = form.get_formatted()
                    grantuser(
                        formatted_dict[config['user_name']],
                        adduser=True
                    )
                    flash("User created", 'success')

        form.append_hidden_entries()

    edit_url = url_for(
        'table', schema=config['user_schema'], table=config['user_table'])
    delete_url = url_for(
        'delete', schema=config['user_schema'], table=config['user_table'])

    data = dynamicform.get_jsontable(
        edit_url, delete_url,
    )

    return render_template(
        'pages/register.html',
        form=form,
        data=data,
        toggle_off_keys=[0]
    )


@app.route('/registeredusers', methods=['GET', 'POST'])
@login_required
def registeredusers():
    """registeredusers
    """
    delete_url = url_for(
        'delete',
        schema=config['user_schema'],
        table=config['user_table'],
        subtable=None)

    return joined_table_template(
        [config.user_table],
        'Registered Users',
        edit_url=url_for(
            'table',
            schema=config['user_schema'],
            table=config['user_table'],
            subtable=None
        ),
        delete_url=delete_url
    )


@app.route('/emergencycontacts', methods=['GET', 'POST'])
@login_required
def emergencycontacts():
    """emergencycontacts
    """
    if not hasattr(config.user_table, 'EmergencyContact'):
        return redirect(url_for('registeredusers'))

    delete_url = url_for(
        'delete',
        schema=config['user_schema'],
        table=config['user_table'],
        subtable=None)

    return joined_table_template(
        [config.user_table.EmergencyContact],
        'Emergency Contacts',
        edit_url=url_for(
            'table',
            schema=config['user_schema'],
            table=config['user_table'],
            subtable=None
        ),
        delete_url=delete_url
    )


@app.route('/registergroup', methods=['GET', 'POST'])
@login_required
def registergroup():
    """setup a group
    """

    if current_user.user_name not in config['administrators']:
        flash("Only administrators are allowed to register groups", "warning")
        return redirect(url_for('home'))

    group_class = config.group_table

    dynamicform, form = config.get_dynamicform(
        f'{config["group_schema"]}.{config["group_table"]}',
        group_class, DynamicForm
    )

    if request.method == 'POST':
        submit = request.form.get('submit', None)

        form.rm_hidden_entries()

        if submit == 'Register':
            if form.validate_on_submit():
                try:
                    dynamicform.insert(form)
                except dj.DataJointError as e:
                    flash(f"{e}", 'error')
                else:
                    dynamicform.reset()
                    config.create_group_schemas()
                    flash("Project group created", 'success')

        form.append_hidden_entries()

    edit_url = url_for(
        'table', schema=config['group_schema'], table=config['group_table'])
    delete_url = url_for(
        'delete', schema=config['group_schema'], table=config['group_table'])

    data = dynamicform.get_jsontable(
        edit_url, delete_url,
    )

    return render_template(
        'pages/group.html',
        form=form,
        data=data,
        toggle_off_keys=[0]
    )


@app.route('/assigngroup', methods=['GET', 'POST'])
@login_required
def assigngroup():
    """setup a group
    """

    if current_user.user_name not in config['administrators']:
        flash("Only administrators are allowed to assign groups", "warning")
        return redirect(url_for('home'))

    # only assign yourself to a group
    # TODO what should the authorization behavior be?
    kwargs = {
        config['user_name']: current_user.user_name
    }

    if current_user.user_name in config['administrators']:
        readonly = []
    else:
        readonly = [config['user_name']]

    group_class = config.assigned_table

    dynamicform, form = config.get_dynamicform(
        f'{config["assignedgroup_schema"]}.{config["assignedgroup_table"]}',
        group_class, DynamicForm, **kwargs
    )

    if request.method == 'POST':
        submit = request.form.get('submit', None)

        form.rm_hidden_entries()

        if submit == 'Register':
            if form.validate_on_submit():
                try:
                    formatted_dict = dynamicform.insert(form)
                except dj.DataJointError as e:
                    flash(f"{e}", 'error')
                else:
                    dynamicform.reset()
                    config.create_group_schemas()
                    config.refresh_permissions()
                    user = formatted_dict[config['user_name']]
                    group = formatted_dict[config['group_name']]
                    grantprivileges(
                        user,
                        config['connection'],
                        {f'{group}.*': 'ALL PRIVILEGES'}
                    )
                    flash(
                        f"Project {group} now includes user {user}",
                        'success'
                    )

        form.append_hidden_entries()

    delete_url = url_for(
        'delete',
        schema=config["assignedgroup_schema"],
        table=config["assignedgroup_table"])

    data = dynamicform.get_jsontable(
        delete_url=delete_url,
    )

    return render_template(
        'pages/assigngroup.html',
        form=form,
        data=data,
        toggle_off_keys=[0],
        readonly=readonly
    )



@app.route(f"{config['tmp_folder']}/<path:filename>")
@login_required
def tmpfile(filename):
    return send_from_directory(config['tmp_folder'], filename)
