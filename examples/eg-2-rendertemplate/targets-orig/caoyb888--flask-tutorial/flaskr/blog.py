from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint('blog', __name__)

@bp.route('/')
def index():
    db = get_db()
    if g.user is not None:
        posts = db.execute(
            'SELECT p.id, title, body, created, p.author_id author_id, username, e.id eid'
            ' FROM post p JOIN user u ON p.author_id = u.id'
             ' left outer join enjoy e on e.post_id = p.id  and e.author_id = ?'
             ' ORDER BY created DESC',
            ( g.user['id'],)
         ).fetchall()
    else:
        posts = db.execute(
            'SELECT p.id, title, body, created, p.author_id author_id, username, e.id eid'
            ' FROM post p JOIN user u ON p.author_id = u.id'
             ' left outer join enjoy e on e.post_id = p.id  and e.author_id = -1'
             ' ORDER BY created DESC'           
         ).fetchall()

    postcomm = db.execute(
        'Select post_id pid,author_id uid,body from comment '
    ).fetchall()

    return render_template('blog/index.html', posts=posts,postscomm=postcomm)

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO post (title, body, author_id)'
                ' VALUES (?, ?, ?)',
                (title, body, g.user['id'])
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/create.html')

def get_post(id, check_author=True):
    post = get_db().execute(
        'SELECT p.id, title, body, created, p.author_id author_id, username, e.id eid'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' left outer join enjoy e on e.post_id = p.id  and e.author_id = ?'
        ' WHERE p.id = ?',
        (g.user['id'],id)
    ).fetchone()

    if post is None:
        abort(404, "Post id {0} doesn't exist.".format(id))

    if check_author and post['author_id'] != g.user['id']:
        abort(403,"Post id {0} is not your created.".format(id))

    return post

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE post SET title = ?, body = ?'
                ' WHERE id = ?',
                (title, body, id)
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/update.html', post=post)

@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.execute('DELETE FROM comment where id = ?', (id,))
    db.execute('DELETE FROM post WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('blog.index'))



@bp.route('/<int:id>/view')
@login_required
def view(id):
    post = get_post(id,check_author=False)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE post SET title = ?, body = ?'
                ' WHERE id = ?',
                (title, body, id)
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/view.html', post=post)


@bp.route('/<int:id>/<int:enjoy_true>/enjoy', methods=('GET', 'POST'))
@login_required
def enjoy(id,enjoy_true):
    
    db = get_db()
    if enjoy_true == 1:
        db.execute('delete from enjoy where author_id = ? and post_id = ?',(g.user['id'], id))
    else:
        db.execute('insert into enjoy(author_id,post_id) values(?,?)',(g.user['id'], id))
    db.commit()
    return redirect(url_for('blog.index'))


@bp.route('/<int:id>/createcomm', methods=('GET', 'POST'))
@login_required
def createcomm(id):
    post = get_post(id)
    if request.method == 'POST':
        body = request.form['body']
        error = None

        if not body:
            error = 'Comment is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO comment (post_id, body, author_id)'
                ' VALUES (?, ?, ?)',
                (id, body, g.user['id'])
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/createcomm.html',post=post)

def get_comment(id):
    db = get_db()
    postcomm = db.execute(
        'Select post_id pid,author_id uid,body from comment where post_id = ?',
        (id,)
    ).fetchall()
    return postcomm

def init_comment(app):
    app.add_template_filter(get_comment,"getcomment")
    