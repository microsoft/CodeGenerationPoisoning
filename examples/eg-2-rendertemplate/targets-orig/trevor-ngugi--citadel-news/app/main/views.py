from flask import render_template
from . import main
from ..request import get_top_news,get_sources

# Views
@main.route('/')
def index():

    '''
    View root page function that returns the index page and its data
    '''
    top_news = get_top_news()
    print(top_news)
    news_sources=get_sources()
    print(news_sources)
    return render_template('index.html',top_news = top_news,sources =news_sources)