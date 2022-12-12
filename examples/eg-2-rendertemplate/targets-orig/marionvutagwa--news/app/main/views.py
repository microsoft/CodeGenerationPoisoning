from flask import render_template,request,redirect,url_for
from . import main
from ..requests import get_sources,get_article,get_articles

# Views
@main.route('/')
def index():
    '''
    View root page function that returns the index page and data
    '''
    General_news = get_sources()
    title = "Home - New highlight"
    search_sources = request.args.get('source_query')
    if search_sources:
        return redirect(url_for('search',sources_name=search_sources))
    else:
        return render_template('index.html', title = title,news = General_news)

@main.route('/articles/<id>')
def articles(id):
    '''
    view articles page function that return  articles detail page
    '''
    articles = get_article(id)
    title = f'(articles.title)'
    cnn_news = get_articles('cnn') 
    # BBC_News =get_articles('bbc_news')
    return render_template('articles.html',title = title, articles = articles,cnn = cnn_news) 

@main.route('/search/<sources_name>')
def search(main_search):
    '''
    View function to display the search results
    '''
    sources_name_list = main_search.split(" ")
    sources_name_format = "+".json(sources_name_list)  
    searched_sources = search_sources(sources_name_format)
    title = f'search result for {sources_name}'
    return render_template('search.html',sources = searched_sources)  