from app import app
from flask import render_template, request, redirect, url_for
from .request import get_news, get_newsarticle
from app.models import article
from .forms import articleForm

# Article = Article.article



@app.route('/')
def index():

    news = get_news()    

    return render_template('index.html', sources=news)


@app.route('/news/<news_id>')
def news(news_id):
    articles = get_newsarticle(news_id)
    name = news_id
    # article = article.get_article(news.id)
    
    return render_template('news.html', name=name, articles = articles)


# @app.route('/search/<news_name>')
# def search(news_name):
#     news_name_list = news_name.split('')
#     news_name_format = + (news_name_list)
#     # search_news = (news_name_format)
#     # news = "f{news_name}"
#     return render_template('search.html,news = searched_news')


# @app.route('/news/article/new/<int:id>', methods=['GET POST'])
# def new_article(id):
#     form = articleForm()
#     news = get_news()

#     if form.validate_on_submit():
#         name = form.name.data
#         article = form.article.data
#         new_article = article(id, name, article)
#         new_article.save_article()
#         return redirect(url_for('news', id=id))

#     name = 'f {name}'
#     return render_template('new_article.html', name=news, article_form=form, news=news)
