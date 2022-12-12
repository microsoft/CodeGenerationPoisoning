from flask import (
    Blueprint, redirect, render_template, url_for
)
from keyphrases.db import get_db


bp = Blueprint('results', __name__)

@bp.route('/')
def index():
    db = get_db()
    docs = db.execute(
        'SELECT id, title, kp_count FROM documents ORDER BY created DESC'
        ).fetchall()
    return render_template('results/index.html', docs=docs)

def get_kp(id):
    kp = get_db().execute(
        'SELECT * FROM documents WHERE id = ?', (id,)
        ).fetchone()
    return kp


@bp.route('/<int:id>/view', methods=('GET', 'POST'))
def view(id):
    kp = get_kp(id)
    return render_template('results/view.html', kp=kp)


@bp.route('/<int:id>/delete', methods=('POST',))
def delete(id):
    get_kp(id)
    db = get_db()
    db.execute('DELETE FROM documents WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('results.index'))
