from flask import render_template,request,redirect,url_for
from . import main
from ..request import get_Source_news,get_article ,get_category,get_headlines
from ..models import Source


# Views
@main.route('/')
def index():

    '''
    View root page function that returns the index page and its data
    '''
   
    latest_news = get_Source_news()
    headlines = get_headlines()
    
    title = 'Welcome to The best News Article Website Online'

    return render_template('index.html',title = title,latest=latest_news, headlines = headlines)


@main.route('/news/<id>')
def article(id):
    articles = get_article(id)
    return render_template('articles.html' , articles = articles)


@main.route('/technology')
def tech_cat():
    categories = get_category("technology")
    return render_template('categories.html',categories = categories)
@main.route('/business')
def business_cat():
    categories =  get_category("business")
    return render_template('categories.html',categories = categories)

@main.route('/entertainment')
def enta_cat():
    categories =  get_category("/entertainment")
    return render_template('categories.html',categories = categories)

@main.route('/science')
def science_cat():
    categories =  get_category("science")
    return render_template('categories.html',categories = categories)

@main.route('/sports')
def sport_cat():
    categories =  get_category("sports")
    return render_template('categories.html',categories = categories)



