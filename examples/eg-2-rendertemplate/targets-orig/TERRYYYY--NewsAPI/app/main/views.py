from flask import render_template
from . import main
from ..request import get_news,get_article

@main.route('/')
def index():
    trending_news = get_news('trending')

    return render_template('index.html',trending=trending_news)

@main.route('/articles/<id>')
def article(id):
    article = get_article(id)
    source=id
    return render_template('article.html',article = article,source=source)