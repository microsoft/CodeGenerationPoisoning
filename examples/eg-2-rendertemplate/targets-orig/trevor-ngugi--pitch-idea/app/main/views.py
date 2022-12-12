from flask import render_template,request,redirect,url_for,abort
from . import main
from flask_login import login_required,current_user
from .forms import PostForm, CommentForm, UpdateProfile
from ..models import User,Post
from .. import db,photos

@main.route("/", methods = ["GET", "POST"])
@login_required
def index():
    """
    View root page function that returns the index page and its data
    """
    all_posts = Post.query.all()
    post_form = PostForm()
    title = "pitch idea"

    if post_form.validate_on_submit():
        post_title = post_form.title.data
        post_form.title.data = ""
        post_content = post_form.post.data
        post_form.post.data = ""
        post_category = post_form.category.data
        new_post = Post(post_title = post_title,
                        post_content = post_content,
                        category = post_category,
                        user_id = current_user.id)

        new_post.save_post()
        return redirect(url_for("main.index"))
    
    return render_template("index.html",title = title,post_form = post_form,all_posts = all_posts)

@main.route("/post/<int:id>", methods = ["GET", "POST"])
def post(id):
    user = User.query.filter_by(id = id).first()
    post = Post.query.filter_by(post_id = id).first()
    title = post.post_title
    comments = Comment.query.filter_by(post_id = id).all()
    comment_form = CommentForm()

    if comment_form.validate_on_submit():
        comment = comment_form.comment.data
        comment_form.comment.data = ""
        new_comment = Comment(comment = comment, 
                            post_id = id,
                            user_id = id)
        new_comment.save_comment()
        return redirect(url_for("main.post", id = post.post_id))

    return render_template("post.html",
                            post = post,
                            title = title,
                            comments = comments,
                            comment_form = comment_form,
                            user = user)

@main.route("/profile/<uname>/")#<int:id>
def profile(uname):
    user = User.query.filter_by(username = uname).first()
    #posts = Post.query.filter_by(user_id = id).all()
    #title = user.full_name

    return render_template("profile/profile.html",
                            user = user,
                           # posts = posts,
                            #title = title
                            )

@main.route("/profile/<int:id>/update", methods = ["GET", "POST"])
def update(id):
    user = User.query.filter_by(id = id).first()
    title = user.full_name
    if user is None:
        abort(404)

    form = UpdateProfile()
    if form.validate_on_submit():
        user.bio = form.bio.data
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("main.profile",
                                id = id))

    return render_template("profile/update.html",
                            form = form,
                            user = user,
                            title = title)

@main.route("/profile/<int:id>/update/pic", methods = ["POST"])
def update_pic(id):
    user = User.query.filter_by(id = id).first()
    if "photo" in request.files:
        filename = photos.save(request.files["photo"])
        path = f"photos/{filename}"
        user.profile_pic_path = path
        db.session.commit()
    return redirect(url_for("main.update",
                                id = id))

@main.route("/users")
def users():
    users = User.query.all()
    title = "Browse users"
    return render_template("users.html", 
                            users = users,
                            title = title)

@main.route("/category/<cname>")
def category(cname):
    posts = Post.query.filter_by(category = cname).all()
    title = cname

    return render_template("category.html",
                            title = title,
                            posts = posts)

@main.route("/about")
def about():
    title = "About 60 Seconds"
    return render_template("about.html",
                            title = title)
    