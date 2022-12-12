from us_states import postal_abbreviations

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

bp = Blueprint('address_form', __name__, url_prefix='/')


@bp.route('/search', methods=('GET', 'POST'))
@bp.route('/')
def search():
    """Take in an address."""
    if request.method == 'POST':
        return render_template('election_results.html')

    return render_template('address_form.html', states=postal_abbreviations)
