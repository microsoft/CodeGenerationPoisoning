from typing import Any
from typing import Dict

import pandas as pd
from flask import Blueprint
from flask import current_app
from flask import flash
from flask import render_template

from app.data.database import get_current_time
from app.data.globals import boathouses
from app.data.globals import cache
from app.data.globals import reaches
from app.data.globals import website_options
from app.data.models.prediction import get_latest_prediction_time


bp = Blueprint('flagging', __name__)


@bp.before_request
@cache.cached()  # <-- needs to be here. some issues occur if you exclude it.
def before_request():
    last_pred_time = get_latest_prediction_time()
    current_time = get_current_time()
    # Calculate difference between now and latest prediction time
    # If model_outputs has zero rows, we raise the following error:
    # > TypeError: unsupported operand type(s) for -: 'Timestamp' and 'NoneType'
    # In this case, just have diff be None.
    if last_pred_time is not None:
        diff = current_time - last_pred_time
    else:
        diff = None

    # If more than 48 hours, flash message.
    if current_app.env == 'demo':
        flash(
            'This website is currently in demo mode. It is not using live data.'
        )
    elif diff is None:
        flash(
            'A unknown error occurred. It is likely that the database does not '
            'contain any data. Please contact the website administrator.'
        )
    elif diff is not None and diff >= pd.Timedelta(24, 'hr'):
        flash(
            '<b>Note:</b> The database has not updated in at least 24 hours. '
            'The information displayed on this page may be outdated.'
        )

    # ~ ~ ~

    if not website_options.boating_season:
        flash(
            '<b>Note:</b> It is currently not boating season. We do not '
            'display flags when it is not boating season. We hope to see you '
            'again in the near future!'
        )


def flag_widget_params(force_display: bool = False) -> Dict[str, Any]:
    """Creates the parameters for the flags widget.

    Pass these parameters into a Jinja template like this:

    >>> **flag_widget_params()
    """
    return dict(
        boathouses=boathouses,
        website_options=website_options,
        model_last_updated_time=get_latest_prediction_time(),
        boating_season=force_display or website_options.boating_season,
        flagging_message=website_options.rendered_flagging_message
    )


@bp.route('/')
@cache.cached()
def index() -> str:
    """
    The home page of the website. This page contains a brief description of the
    purpose of the website, and the latest outputs for the flagging model.
    """
    return render_template('index.html',
                           **flag_widget_params())


@bp.route('/boathouses')
@cache.cached()
def boathouses_page() -> str:
    return render_template('boathouses.html',
                           **flag_widget_params(force_display=True))


@bp.route('/about')
@cache.cached()
def about() -> str:
    return render_template('about.html')


@bp.route('/model')
@cache.cached()
def model_outputs() -> str:
    """
    Parses the model outputs in a human readable format. It also gets the
    boathouses by reach, so the user knows what boathouses are associated with
    each reach.

    Returns:
        Rendering of the model outputs via the `model_outputs.html` template.
    """
    return render_template('model_outputs.html', reaches=reaches)


@bp.route('/flags')
@bp.route('/flags/<int:version>')
@cache.cached()
def flags(version: int = None) -> str:
    return render_template('flags.html',
                           **flag_widget_params(),
                           version=version)


@bp.route('/api')
@cache.cached()
def api_index() -> str:
    """Landing page for the API."""
    return render_template('api/index.html')
