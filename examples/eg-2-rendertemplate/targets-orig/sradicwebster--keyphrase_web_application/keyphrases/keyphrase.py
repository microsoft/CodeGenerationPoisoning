from flask import (
    Blueprint, flash, redirect, render_template, request, url_for
)
from keyphrases.db import get_db
from .nlp_models import PublicationKeyPhrase


bp = Blueprint('keyphrase', __name__, url_prefix='/keyphrase')

@bp.route('/input', methods=('GET', 'POST'))
def input():
    if request.method == 'POST':
        title = request.form['title']
        text = request.form['text']

        db = get_db()
        error = None
        if not title:
            error = 'Title is required'
        elif not text:
            error = 'Text is required'
        elif db.execute(
            'SELECT id FROM documents WHERE title = ?', (title,)
        ).fetchone() is not None:
            error = f'Title "{title}" is already used'

        if error is None:
            publication = PublicationKeyPhrase(text)
            kp_list = publication.get_key_phrases_hmm()
            number_of_kp = len(kp_list)
            if number_of_kp == 0:
                error = f'No key phrases identified for "{title}"'
            else:
                keyphrases = '\n'.join(set(kp_list))

                db.execute(
                    'INSERT INTO documents (title, text, keyphrases, kp_count) VALUES (?, ?, ?, ?)',
                    (title, text, keyphrases, number_of_kp) )
                db.commit()
                return redirect(url_for('index'))

        flash(error)

    return render_template('keyphrase/input.html')
