import re
from app import app, redis
from flask import abort, redirect, render_template, request, url_for

from .compression import CompressionLink

comp = CompressionLink()

regex = re.compile(
    r'^(?:http|ftp)s?://'  # http:// or https://
    # domain...
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)


@app.errorhandler(404)
def page_not_found(error):
    """return 404 not found page"""
    return render_template('404.html', title='404'), 404


def create_short_link():
    """
    post:
        create short link
    get:
        show short link if previous request was post short link 
    """
    full_link, short_link = None, None

    if request.method == 'POST':
        if not re.match(regex, request.form['full_link']):
            abort(400, 'Link is broken')
        full_link = request.form['full_link']
        redis.incr('linked_id')
        counter = int(redis.get('linked_id'))
        short_link = comp.compress_url(counter)
        redis.set(short_link, full_link, nx=True)
        short_link = request.url + short_link
        app.logger.info(f'create short link: {short_link}')
    return render_template('main.html', context={'full_link': full_link, 'short_link': short_link})


def get_short_link(short_link):
    """
    get: redirect to full link permanent
    """
    full_link = redis.get(short_link)
    if full_link is None:
        abort(404)
    app.logger.info(f' short link {short_link} redirect to: {full_link}')
    return redirect(full_link, code=302)
