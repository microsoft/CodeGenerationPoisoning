from . import main
from flask import render_template,redirect,url_for,request,abort
from flask_login import login_required,current_user,login_user,logout_user
from .forms import ArticleUploadForm,CommentsForm,UpdateProfile
from .. import db,photos
from ..models import Article,Comment,User,  Quotes
from ..requests import getQuotes

@main.route('/')
def index():
    articles = Article.get_article()
    try:
        quotes = getQuotes()
    except Exception as e:
        quotes = "quotes unavailable"
    title='Welcome to the article'
    return render_template('index.html',articles=articles,quotes = quotes)

@main.route('/addarticle',methods = ['GET','POST'])
@login_required
def add_article():
    form = ArticleUploadForm()
    if form.validate_on_submit():
        article = form.article.data
        category = form.category.data
        new_article = Article(article = article,category = category,user = current_user)
        new_article.save_article()
        return redirect(url_for('.index'))
    title = 'Add a article'
    return render_template('addarticle.html',title = title,articleform = form)


@main.route('/articlediscussion/<int:article_id>/comment',methods=['POST','GET'])
@login_required
def comment(article_id):
    current_article = Article.query.filter_by(id = article_id).first()
    if request.method == "POST":
        comment = request.form.get("comment")
        new_comment = Comment(comment = comment,user = current_user,article = current_article)
        db.session.add(new_comment)
        db.session.commit()
    article = Article.query.get_or_404(article_id)
    comments = Comment.get_comments(article_id)

    title = 'Article Discussion'
    return render_template('articlediscussion.html',title = title,article = article,comments=comments)

@main.route('/profile/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username = username).first()
    userid = user.id
    my_articles = Article.query.filter_by(user_id = userid).all()

    if user is None:
        abort(404)

    return render_template('profile/profile.html',user = user,my_articles = my_articles)

@main.route('/user/<username>/update', methods = ['GET','POST'])
@login_required
def profle_update(username):
    user = User.query.filter_by(username = username).first()
    form = UpdateProfile()
    if form.validate_on_submit():
        user.bio = form.bio.data
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('.profile',username = user.username))

    return render_template('profile/update.html',form= form)

@main.route('/user/<username>/update/pic',methods= ['POST'])
@login_required
def update_pic(username):
    user = User.query.filter_by(username = username).first()
    if 'photo' in request.files:
        filename = photos.save(request.files['photo'])
        path = f'photos/{filename}'
        user.profile_pic_path = path
        db.session.commit()
    return redirect(url_for('main.profile',username=username))

@main.route('/articlediscussion/<int:article_id>/update',methods=['POST','GET'])
@login_required
def update(article_id):
    current_article = Article.query.filter_by(id = article_id).first()
    if current_article.user != current_user:
        abort(403)
    form = ArticleUploadForm()
    if form.validate_on_submit():
        current_article.article = form.article.data
        current_article.category = form.category.data
        db.session.commit()
        return redirect('.comment',article_id = article_id)
    elif request.method == 'GET':
        form.category.data = current_article.category
        form.article.data = current_article.article
    return render_template('addarticle.html',title = 'update article',articleform = form)


@main.route('/articlediscussion/<int:article_id>/delete',methods=['POST'])
@login_required
def delete(article_id):
    current_article = Article.query.filter_by(id = article_id).first()
    if current_article.user != current_user:
        abort(403)
    db.session.delete(current_article)
    db.session.commit()
    return redirect(url_for('.index'))