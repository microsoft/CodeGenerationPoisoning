from flask import Blueprint, flash,redirect,url_for,render_template,abort,request
from app.posts.forms import PostForm
from flask_login import login_required, current_user
from app.models import Post
from app import db
from app.posts.utils import save_picture

posts = Blueprint('posts',__name__)


@posts.route('/posts/new', methods =['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    picture_file = 'blog.jpg'
    if form.validate_on_submit():
        print(form.picture.data)
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
        post = Post(title=form.title.data,content = form.content.data, category= form.category.data, summary = form.summary.data, image_file = picture_file, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('main.home'))
    return render_template('create_post.html',form = form, legend = "Create Post")

@posts.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, post=post)

@posts.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        if form.picture.data:
            print('Hello World')
            picture_file = save_picture(form.picture.data)
            post.image_file = picture_file
        post.title = form.title.data
        post.content = form.content.data
        post.category = form.category.data
        post.summary = form.summary.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('posts.post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
        form.category.data = post.category
        form.summary.data = post.summary
    return render_template('create_post.html', title='Update Post',
                           form=form, legend='Update Post')


@posts.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('main.home'))