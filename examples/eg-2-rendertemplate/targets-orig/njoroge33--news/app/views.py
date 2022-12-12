from app import app
from flask import render_template
from .request import get_sources, get_articles

@app.route('/')
def index():
    sources = get_sources()
    return render_template('index.html', sources = sources)

@app.route('/articles/<source_id>')
def article(source_id):
    articles = get_articles(source_id)
    return render_template('article.html', id = source_id, articles=articles)