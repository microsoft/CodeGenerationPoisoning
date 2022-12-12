from flask import render_template, request, redirect,url_for,abort
from . import main
from ..requests import get_quote
from flask_login import login_required,current_user
from .forms import UpdateProfile,BlogForm,CommentForm
from .. import db,photos
from ..models import User, Blog, Comment, PhotoProfile, Upvote, Downvote, Subscriber
from flask_mail import Mail
import markdown2

#views
@main.route('/')
def index():
    '''
    view root page that retunrs index page with its data
    '''
    title = 'JVUNE | Welcome to JVUNE Blogs'
    quote = get_quote()

    return render_template('index.html', title=title, quote=quote)    
    
@main.route('/user/<uname>')
def profile(uname):
    user = User.query.filter_by(username = uname).first()

    title = f"{uname.capitalize()}'s Profile"

    if user is None:
        abort(404)

    return render_template('profile/profile.html', user=user, title=title)

@main.route('/user/<uname>/update',methods = ['GET','POST'])
@login_required
def update_profile(uname):
    user = User.query.filter_by(username = uname).first()
    if user is None:
        abort(404)

    form = UpdateProfile()

    if form.validate_on_submit():
        user.bio = form.bio.data

        db.session.add(user)
        db.session.commit()

        return redirect(url_for('.profile',uname=user.username))

    return render_template('profile/update.html',form =form)

@main.route('/user/<uname>/update/pic',methods= ['POST'])
@login_required
def update_pic(uname):
    user = User.query.filter_by(username = uname).first()
    if 'photo' in request.files:
        filename = photos.save(request.files['photo'])
        path = f'photos/{filename}'
        user.profile_pic_path = path
        db.session.commit()
    return redirect(url_for('main.profile',uname=uname))

@main.route('/blogs/new', methods = ['GET','POST'])
@login_required
def new_blog():
    
    form = BlogForm()
    if form.validate_on_submit():
        author = form.author.data
        blog = form.text.data

        new_blog = Blog(blog_author = author,blog_content = blog, user = current_user)
        new_blog.save_blog()
        

        return redirect(url_for('main.blogs'))

    title = 'New Blog'
    return render_template('new_blog.html',blog_form=form)

@main.route('/blog/comment/delete/<int:id>', methods = ['GET', 'POST'])
@login_required
def delete_comment(id):
    comment = Comment.query.filter_by(id=id).first()
    blog_id = comment.blog
    Comment.delete_comment(id)

    return redirect(url_for('main.blog',id=blog_id))

@main.route('/blog/<int:id>', methods = ["GET","POST"])
def blog(id):
    blog = Blog.get_blog(id)
    posted_date = blog.posted.strftime('%b %d, %Y')
    

    form = CommentForm()
    if form.validate_on_submit():
        comment = form.text.data
        name = form.name.data

        new_comment = Comment(comment = comment, name = name, blog_id = blog)

        new_comment.save_comment()

    comments = Comment.get_comments(blog)

    return render_template('blog.html', blog = blog, comment_form = form,comments = comments, date = posted_date)

@main.route('/user/<uname>/blogs', methods = ['GET','POST'])
def user_blogs(uname):
    user = User.query.filter_by(username = uname).first()
    blogs = Blog.query.filter_by(user_id = user.id).all()

    return render_template('profile/blogs.html', user = user, blogs = blogs)

@main.route('/blogs', methods = ['GET','POST'])
def blogs():
    blogs = Blog.query.order_by(Blog.id.desc()).limit(5)
    likes = Upvote.query.all()
    

    return render_template('blogs.html',blogs = blogs,likes = likes)

@main.route('/blog/<int:id>/update', methods = ['GET','POST'])
@login_required
def update_blog(id):
    
    blog = Blog.get_blog(id)
    form = BlogForm()
    if form.validate_on_submit():
        blog.blog_author = form.author.data
        blog.blog_content = form.text.data
        
        db.session.commit()
        return redirect(url_for('main.blogs', id = id))
    elif request.method == 'GET':
        form.author.data = blog.blog_author
        form.text.data = blog.blog_content
    
    return render_template('new_blog.html', blog_form=form, id=id)

@main.route('/like/<int:id>', methods=['POST', 'GET'])
@login_required
def upvote(id):
    blog = Blog.query.get(id)
    vote_mpya = Upvote(blog=blog, upvote=1)
    vote_mpya.save()
    return redirect(url_for('main.blogs'))

    return render_template('blog.html', blog = blog, comment_form = form,comments = comments, date = posted_date)

@main.route('/dislike/<int:id>', methods=['GET', 'POST'])
@login_required
def downvote(id):
    blog = Blog.query.get(id)
    vm = Downvote(blog=blog, downvote=1)
    vm.save()
    return redirect(url_for('main.blog'))

    return render_template('blog.html', blog = blog, comment_form = form,comments = comments, date = posted_date)

# @main.route('/subscribe', methods=['GET','POST'])
# def subscriber():
#     subscriber_form=SubscriberForm()
#     blogs = Blog.query.order_by(Blog.posted.desc()).all()
#     subscriber = Blog.query.all()

#     blogs = Blog.query.all()

#     if subscriber_form.validate_on_submit():
#         subscriber= Subscriber(email=subscriber_form.email.data,name = subscriber_form.name.data)

#         db.session.add(subscriber)
#         db.session.commit()

#         #mail_message("Welcome to JVUNE","email/welcome_subscriber",subscriber.email,subscriber=subscriber)

#         title= "JVUNE"
#         return redirect(url_for('main.blogs', title=title, blog=blog, subscriber_form=subscriber_form))


#     return render_template('subscribe.html',subscriber=subscriber,subscriber_form=subscriber_form,blog=blog)    