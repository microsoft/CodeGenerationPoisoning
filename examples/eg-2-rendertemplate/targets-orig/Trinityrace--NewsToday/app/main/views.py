from flask import render_template,request,redirect,url_for
from . import main
from  ..request import get_news 
#from  .. import News

# Views

@main.route('/')
def index():
    headline_news=get_news()
    print(headline_news)
    #return render_template('index.html',headlines=headline_news)

    return render_template('headline.html',headlines=headline_news)


# @main.route('/f')

# def indexx():
#     # get general news

#     general_news = get_news('category')
#     business_news = get_news('business')
#     entertainment_news = get_news('entertainment')
#     sports_news = get_news('sports')
#     technology_news = get_news('technology')
#     science_news = get_news('science')
#     health_news = get_news('health')


#     title = 'News Today Site'

#     return render_template('index.html', title=title, General=general_news, Business=business_news,
#                            Entertainment=entertainment_news, Sports=sports_news, Technology=technology_news,
#                            Science=science_news, Health=health_news)
    # # Getting popular news
    # popular_news = get_news('popular')
    # # print(popular_news)
    # upcoming_news = get_news('upcoming')
    # now_showing_news = get_news('now_playing')
    # title = 'Home - Welcome to The best News Review Website Online'
    # return render_template('index.html', title = title, popular = popular_news, upcoming = upcoming_news, now_showing = now_showing_news )

@main.route('/articles/<news_id>&<int:per_page>')
def articles(articles_id, per_page):
    '''
    Function that returns articles based on their sources
    '''

    articles_source = get_articles(news_id, per_page)
    title = f'{articles_id} | All Articles'
    return render_template('articles.html', title=title, name=articles_id, news= articles_source)
