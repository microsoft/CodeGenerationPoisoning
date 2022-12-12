from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from werkzeug.exceptions import abort

from reliquary.auth import login_required
from reliquary.db import get_db

# TODO add url prefix for this presets page once the landing page is figured out
bp = Blueprint('presets', __name__)

def get_preset(id, check_author=True):
    preset = get_db().execute(
        'SELECT p.id, title, body, created, author_id, username'
        ' FROM preset p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()

    if preset is None:
        abort(404, "Preset id {0} does not exist.".format(id))

    if check_author and preset['author_id'] != g.user['id']:
        abort(403)
    return preset

@bp.route('/')
def index():
    """Show all presets, most recent first."""
    db = get_db()
    presets = db.execute(
        'SELECT p.id, title, body, created, author_id, username'
        ' FROM preset p JOIN user u ON p.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()
    return render_template('presets/index.html', presets=presets)

@bp.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        body=request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO preset (title, body, author_id)'
                ' VALUES (?, ?, ?)', (title, body, g.user['id'])
            )
            db.commit()
            return redirect(url_for('presets.index'))
    return render_template('presets/create.html')

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    preset = get_preset(id)

    if request.method == 'POST':
        title = request.form['title']
        body=request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE preset SET title = ?, body = ?'
                ' WHERE id = ?',
                (title, body, id)
            )
            db.commit()
            return redirect(url_for('presets.index'))

    return render_template('presets/update.html', preset=preset)

@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_preset(id)
    db = get_db()
    db.execute('DELETE FROM preset WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('presets.index'))
