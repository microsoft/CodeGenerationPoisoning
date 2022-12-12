from flask import render_template,redirect,url_for,request
from . import main
from ..models import Sources
from ..request import get_articles,get_news_sources

@main.route('/')
def index():
    '''
    Function that returns the index page and the processed data
    '''
    general_news = get_news_sources('general')
    business_news = get_news_sources('business')
    entertainment_news = get_news_sources('entertainment')
    sports_news = get_news_sources('sports')
    technology_news = get_news_sources('technology')
   
    title = 'Homepage'
    
    return render_template('index.html',title=title, general=general_news, business=business_news, entertainment=entertainment_news, sports=sports_news, technology=technology_news)

@main.route('/articles/<id>')
def articles(id):
    '''
    Function to view articles page
    '''
    news_articles = get_articles(id)
    title = f'{id}'
    return render_template('articles.html',title= title,articles = news_articles)




