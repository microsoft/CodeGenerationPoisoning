from flask import render_template, request, redirect, url_for
from . import main
from ..models import Source, Article
from ..requests import get_sources, get_articles, search_article

#views
@main.route('/')
def index():
    '''
    view root function that returns the index page and its data
    '''

    business_news = get_sources('business')
    entertainment_news = get_sources('entertainment')
    general_news = get_sources('general')
    health_news = get_sources('health')
    science_news = get_sources('science')
    sports_news = get_sources('sports')
    technology_news = get_sources('technology')

    title = 'Welcome to Global News'

    search_article = request.args.get('article_query')

    if search_article:
        return redirect(url_for('.search', article_name = search_article))
    else:
        return render_template('index.html', title=title, business=business_news, entertainment=entertainment_news, general=general_news, health=health_news, science=science_news, sports=sports_news, technology=technology_news)


@main.route('/articles/<source>')
def articles(source):
    '''
    View articles from source
    '''
    articles = get_articles(source)
    return render_template('article.html', articles=articles)

@main.route('/search/<article_name>')
def search(article_name):
    '''
    View function to display the search results
    '''
    article_name_list = article_name.split(" ")
    article_name_format = "+".join(article_name_list)
    searched_articles = search_article(article_name_format)
    title = f'search results for {article_name}'
    return render_template('search.html',articles = searched_articles)    