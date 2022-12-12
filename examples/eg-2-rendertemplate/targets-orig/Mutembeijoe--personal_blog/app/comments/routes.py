from flask import Blueprint, flash, redirect, url_for,render_template
from flask_login import login_required,current_user
from app import db
from app.comments.forms import CommentForm
from app.models import Comment

comments = Blueprint('comment', __name__)


@comments.route('/add_comment/<int:post_id>', methods = ['GET', 'POST'])
@login_required
def add_comment(post_id):
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(post_id = post_id, description =form.description.data,
                      author=current_user)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment was added!', 'success')
        return redirect(url_for('posts.post', post_id = post_id))
    return render_template('add_comment.html', form=form)
