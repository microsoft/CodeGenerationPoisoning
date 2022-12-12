# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Data Commons static content routes."""

from datetime import date
from flask import Blueprint, render_template, g, current_app
import babel.dates as babel_dates

bp = Blueprint('static', __name__)


@bp.route('/')
def homepage():
    env_name = current_app.config.get('ENV_NAME', None)
    if env_name == 'FEEDINGAMERICA':
        return render_template('private_dc/feedingamerica/homepage.html')
    if env_name == 'IITM':
        # TODO: Update to:
        # return render_template('private_dc/iitm/homepage.html')
        return render_template('static/iitm.html')
    if env_name == 'PRIVATE':
        return render_template('private_dc/default/homepage.html')
    blog_date = babel_dates.format_date(date(2021, 7, 26),
                                        format='long',
                                        locale=g.locale)
    return render_template('static/homepage.html', blog_date=blog_date)


@bp.route('/about')
def about():
    env_name = current_app.config.get('ENV_NAME', None)
    if env_name == 'FEEDINGAMERICA':
        return render_template('private_dc/feedingamerica/about.html')
    return render_template('static/about.html')


@bp.route('/faq')
def faq():
    current_date = date.today().strftime('%-d %b %Y')
    current_year = date.today().strftime('%Y')
    return render_template('static/faq.html',
                           current_date=current_date,
                           current_year=current_year)


@bp.route('/disclaimers')
def disclaimers():
    return render_template('static/disclaimers.html')


@bp.route('/feedback')
def feedback():
    return render_template('static/feedback.html')
