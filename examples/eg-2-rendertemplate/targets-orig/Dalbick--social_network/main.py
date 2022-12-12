from flask import Flask, render_template, redirect, request, abort
from base64 import b64encode
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import func
from flask_restful import Api
from os import environ
from data.db_session import global_init, create_session
from data.users import User
from data.posts import Post
from data.comments import Comment
from register_form import RegisterForm
from login_form import LoginForm
from post_form import PostForm
from comment_form import CommentForm
from user_search_form import UserSearchForm
from post_search_form import PostSearchForm
from users_resources import UsersResource, UsersListResource
from posts_resources import PostsResource, PostsListResource
from comments_resources import CommentsResource, CommentsListResource

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
api = Api(app)
login_manager = LoginManager()
login_manager.init_app(app)


def main():
    global_init('db/social_network.sqlite')
    api.add_resource(UsersListResource, '/api/users')
    api.add_resource(UsersResource, '/api/users/<int:user_id>')
    api.add_resource(PostsListResource, '/api/posts')
    api.add_resource(PostsResource, '/api/posts/<int:post_id>')
    api.add_resource(CommentsListResource, '/api/comments')
    api.add_resource(CommentsResource, '/api/comments/<int:comment_id>')
    port = int(environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)


@app.route('/')
def index():
    session = create_session()
    posts = session.query(Post).all()[::-1]
    return render_template('index.html', posts=posts, title='Posts', index=True)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Registration',
                                   form=form,
                                   message="Password mismatch", registration=True)
        session = create_session()
        if session.query(User).filter(User.nickname == form.nickname.data).first():
            return render_template('register.html', title='Registration',
                                   form=form,
                                   message="Nickname already in use", registration=True)
        user = User(
            surname=form.surname.data,
            name=form.name.data,
            nickname=form.nickname.data,
            age=form.age.data,
            picture=str(b64encode(form.picture.data.read()))[2:-1]
        )
        user.set_password(form.password.data)
        session.add(user)
        session.commit()
        return redirect('/login')
    return render_template('register.html', title='Registration', form=form, registration=True)


@login_manager.user_loader
def load_user(user_id):
    session = create_session()
    return session.query(User).get(user_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = create_session()
        user = session.query(User).filter(User.nickname == form.nickname.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Wrong nickname or password",
                               title='Authorization',
                               form=form)
    return render_template('login.html', title='Authorization', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/post/<int:post_id>')
def post(post_id):
    session = create_session()
    post = session.query(Post).get(post_id)
    if post and (not post.is_private or (current_user.is_authenticated and post.user_id == current_user.id)):
        return render_template('post.html', title='Post', post=post)
    else:
        abort(404)


@app.route('/add_post', methods=['GET', 'POST'])
@login_required
def add_post():
    form = PostForm()
    if form.validate_on_submit():
        session = create_session()
        post = Post()
        post.user_id = current_user.id
        post.picture = str(b64encode(form.picture.data.read()))[2:-1]
        post.description = form.description.data
        post.is_private = form.is_private.data
        session.add(post)
        session.commit()
        return redirect('/post/' + str(post.id))
    return render_template('post_form.html', title='Adding a post',
                           form=form, is_adding=True)


@app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    form = PostForm()
    with open('static/txt/default.txt', 'rb') as f:
        form.picture.data = f
    if request.method == "GET":
        session = create_session()
        post = session.query(Post).get(post_id)
        if not post or current_user != post.user:
            abort(404)
        else:
            form.description.data = post.description
            form.is_private.data = post.is_private
    if form.validate_on_submit():
        session = create_session()
        post = session.query(Post).get(post_id)
        if not post or current_user != post.user:
            abort(404)
        else:
            post.description = form.description.data
            post.is_private = form.is_private.data
            session.commit()
            return redirect('/post/' + str(post.id))
    return render_template('post_form.html', title='Editing a job', form=form, is_adding=False)


@app.route('/delete_post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def delete_job(post_id):
    session = create_session()
    post = session.query(Post).get(post_id)
    if not post or current_user != post.user:
        abort(404)
    else:
        session.delete(post)
        session.commit()
    return redirect('/')


@app.route('/add_comment/<int:post_id>', methods=['GET', 'POST'])
@login_required
def add_comment(post_id):
    session = create_session()
    post = session.query(Post).get(post_id)
    if not post or (post.is_private and post.user_id != current_user.id):
        abort(404)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment()
        comment.user_id = current_user.id
        comment.text = form.text.data
        comment.post_id = post_id
        session.add(comment)
        session.commit()
        return redirect('/post/' + str(post_id))
    return render_template('comment_form.html', title='Adding a comment',
                           form=form)


@app.route('/edit_comment/<int:comment_id>', methods=['GET', 'POST'])
@login_required
def edit_comment(comment_id):
    form = CommentForm()
    if request.method == "GET":
        session = create_session()
        comment = session.query(Comment).get(comment_id)
        if (not comment or current_user.id != comment.user_id or
                (comment.post.is_private and comment.post.user_id != current_user.id)):
            abort(404)
        else:
            form.text.data = comment.text
    if form.validate_on_submit():
        session = create_session()
        comment = session.query(Comment).get(comment_id)
        if (not comment or current_user.id != comment.user_id or
                (comment.post.is_private and comment.post.user_id != current_user.id)):
            abort(404)
        else:
            comment.text = form.text.data
            session.commit()
            return redirect('/post/' + str(comment.post_id))
    return render_template('comment_form.html', title='Editing a comment', form=form)


@app.route('/delete_comment/<int:comment_id>', methods=['GET', 'POST'])
@login_required
def delete_comment(comment_id):
    session = create_session()
    comment = session.query(Comment).get(comment_id)
    if (not comment or current_user.id != comment.user_id or
            (comment.post.is_private and comment.post.user_id != current_user.id)):
        abort(404)
    else:
        post_id = comment.post_id
        session.delete(comment)
        session.commit()
        return redirect('/post/' + str(post_id))


@app.route('/user/<int:user_id>')
def user(user_id):
    session = create_session()
    user = session.query(User).get(user_id)
    if not user:
        abort(404)
    return render_template('user.html', title='User', user=user)


@app.route('/change_picture/<int:user_id>', methods=['GET', 'POST'])
@login_required
def change_picture(user_id):
    if user_id != current_user.id:
        abort(404)
    form = RegisterForm()
    form.nickname.data = form.password.data = form.password_again.data = \
        form.surname.data = form.name.data = '1'
    form.age.data = 1
    if form.validate_on_submit():
        session = create_session()
        user = session.query(User).get(user_id)
        user.picture = str(b64encode(form.picture.data.read()))[2:-1]
        session.commit()
        return redirect('/user/' + str(user_id))
    return render_template('register.html', title='Changing picture', form=form, registration=False)


@app.route('/user_search', methods=['GET', 'POST'])
def user_search():
    form = UserSearchForm()
    if form.validate_on_submit():
        return redirect('/user_search/' + form.nickname.data)
    return render_template('user_search_form.html', title='Find user', form=form)


@app.route('/user_search/<nickname>')
def users(nickname):
    session = create_session()
    users = session.query(User).filter(func.lower(User.nickname).like('%' + nickname.lower() + '%')).all()[::-1]
    return render_template('user_search_result.html', title='Search result', users=users)


@app.route('/post_search', methods=['GET', 'POST'])
def post_search():
    form = PostSearchForm()
    if form.validate_on_submit():
        return redirect('/post_search/' + form.description.data)
    return render_template('post_search_form.html', title='Find post', form=form)


@app.route('/post_search/<description>')
def posts(description):
    session = create_session()
    posts = session.query(Post).filter(func.lower(Post.description).like('%' + description.lower() + '%')).all()[::-1]
    return render_template('index.html', title='Search result', posts=posts, index=False)


if __name__ == '__main__':
    main()
