from flask import render_template, session, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask import current_app, abort

from . import township

from .. import db
from ..models.models import User
from ..decorators import admin_required

from ..models.township import Source, Item

@township.route('/items')
def items():
    return render_template('township/items.html')

@township.route('/sources')
def sources():
    return render_template('township/sources.html')


@township.route('/source/<source_name>')
@login_required
def source(source_name):
    source = Source.query.filter_by(name=source_name).first()
    return render_template('township/source.html', source=source)

@township.route('/item/<item_name>')
@login_required
def item(item_name):
    item = Item.query.filter_by(name=item_name).first()
    ingredients = [
        {
            # popover on names to get quick stats on them
            'name': 'ingredient 1 name',
            'quantity': '1',
            # other info as wanted.
        },
        {
            # popover on names to get quick stats on them
            'name': 'ingredient 2 name',
            'quantity': '2',
            # other info as wanted.
        },
        {
            # popover on names to get quick stats on them
            'name': 'ingredient 3 name',
            'quantity': '3',
            # other info as wanted.
        },

    ]
    return render_template('township/item.html', item=item,
        ingredients=ingredients)

@township.route('/source/<source_name>/popup')
@login_required
def source_popup(source_name):
    source = Source.query.filter_by(name=source_name).first_or_404()
    return render_template('township/source_popup.html',
                user=current_user._get_current_object(),
                name=source_name, source=source)

@township.route('/item/<item_name>/popup')
@login_required
def item_popup(item_name):
    return render_template('township/item_popup.html',
                user=current_user, name=item_name)
