from flask import render_template, request, redirect, url_for
from . import main 
from ..requests import get_sources, get_headlines



# Views    
@main.route('/')
def index():
    
    '''
    View root page function that returns the index page and its data
    '''
    
    #getting business news sources
    business_sources = get_sources('business')
    general_category = get_sources('general')  
    entertainment_category = get_sources('entertainment')
    sports_category = get_sources('sports')
    technology_category = get_sources('technology')
    science_category = get_sources('science')
    health_category =get_sources('health') 
    title = 'Get the latest News  Hightlight '
    return render_template('index.html', title = title, business = business_sources, general = general_category, entertainment = entertainment_category, sports = sports_category, science = science_category, technology = technology_category, health = health_category)




@main.route('/headlines/<id>')
def articles(id):
    '''
    Function that returns articles based on their sources
    '''
    news_source = get_headlines(id)
    title = f'{id} | All Articles'

    return render_template('headlines.html', title = title, name = id, news = news_source)





