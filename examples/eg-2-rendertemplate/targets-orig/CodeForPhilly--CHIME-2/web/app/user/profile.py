# -*- coding: utf-8 -*-
"""User views."""
from flask import render_template
from flask_login import login_required

from app.blueprints import user_profile


@user_profile.route("/")
@login_required
def account():
    """Placeholder restricted route. Testing functionality."""
    return render_template("members.html")
