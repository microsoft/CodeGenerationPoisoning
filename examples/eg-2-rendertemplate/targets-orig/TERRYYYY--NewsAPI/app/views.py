from flask import render_template
from app import app
from .request import get_news
from .request import get_news,get_mynews
from flask import render_template,request,redirect,url_for
#Views
@app.route('/')
def index ():
    '''
    View root page function that returns the index page and its data
    '''
    #Getting trending news
    trending_news = get_news('trending')
    print(trending_news)
    title = 'Habari Chap Chap!'
    return render_template('index.html',title=title,trending=trending_news)

@app.route('/news/<int:id>')
def news(id):
    '''
    View news page function that returns the news details page and its data
    '''
    news = get_mynews(id)
    title = f'{news.name}' 
    return render_template('news.html',name=name,news=news)