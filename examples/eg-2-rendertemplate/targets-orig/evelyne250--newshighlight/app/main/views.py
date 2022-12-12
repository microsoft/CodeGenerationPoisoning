from flask import render_template,request,redirect,url_for
from . import main
from ..request import get_sources, get_articles
from ..models import Sources

# Views
@main.route('/')
def index():

    '''
    View root page function that returns the index page and its data
    '''
    
    new_general = get_sources('general')
    new_business = get_sources('business')
    new_entertainment = get_sources('entertainment')
    new_sports = get_sources('sports')
    new_tech = get_sources('technology')
    new_science = get_sources('science')
    new_health = get_sources('health')

    title = 'Home | Best News Highlight'
    search_news = request.args.get('news_query')

    if search_news:
        return redirect(url_for('search',news_name=search_news))
    else:
        return render_template('index.html',title = title,new_general = new_general, new_business = new_business, new_entertainment = new_entertainment, new_sports = new_sports, new_tech = new_tech, new_science = new_science, new_health = new_health)

@main.route('/articles/<id>')
def articles(id):
   '''
   view articles page
   '''
   print('test')
   print(id)
   articles = get_articles(id)
   # print(articles)
   title = f'NH | {id}'
   return render_template('articles.html',title= title,articles = articles)
