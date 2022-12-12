"""erd-specific views
"""


from flask import render_template, request, flash, url_for, redirect, \
    send_from_directory, session
from functools import wraps
from flask_login import current_user, login_user, login_required, logout_user
import datajoint as dj
import pandas as pd
from ast import literal_eval

from loris import config
from loris.app.app import app
from loris.app.templates import form_template
from loris.app.forms.dynamic_form import DynamicForm
from loris.app.forms.fixed import (
    dynamic_jointablesform, dynamic_settingstableform, LoginForm,
    PasswordForm, dynamic_tablecreationform
)
from loris.app.utils import draw_helper, get_jsontable, user_has_permission
from loris.utils import save_join
from loris.app.login import User
from loris.database.users import grantuser, change_password


@app.route('/erd/', defaults={'schema': None}, methods=['GET', 'POST'])
@app.route('/erd/<schema>', methods=['GET', 'POST'])
@login_required
def erd(schema):

    only_essentials = literal_eval(request.args.get('only_essentials', 'False'))

    filename = draw_helper(
        schema, type='schema', only_essentials=only_essentials
    )

    return render_template(
        'pages/erd.html', filename=filename,
        url=url_for('erd', schema=schema),
        schema=('ERD' if schema is None else schema),
    )
