"""
    Routes
    ~~~~~~
"""
from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required

from loris.app.wiki.processor import Processor
from loris.app.forms.wiki import EditorForm, SearchForm, URLForm
from loris.app.app import app
from loris.app.wiki.current_wiki import current_wiki


@app.route('/wikihome')
@login_required
def wikihome():
    page = current_wiki.get('home')
    app.config['index_dict'] = current_wiki.index_dict()
    if page:
        return wikidisplay('home')
    return render_template('pages/wiki/home.html',
                           index_dict=app.config.get('index_dict', {}))


@app.route('/wikiindex/')
@login_required
def wikiindex():
    pages = current_wiki.index()
    return render_template(
        'pages/wiki/index.html',
        pages=pages, index_dict=app.config.get('index_dict', {}))


@app.route('/wiki/<path:url>/')
@login_required
def wikidisplay(url):
    page = current_wiki.get(url)
    if not page:
        return redirect(url_for('wikicreate', url=url))
    return render_template(
        'pages/wiki/page.html',
        page=page, index_dict=app.config.get('index_dict', {}))


@app.route('/wikicreate/', methods=['GET', 'POST'])
@login_required
def wikicreate():
    url = request.args.get('url', None)
    form = URLForm(url=url)
    if form.validate_on_submit():
        return redirect(url_for(
            'wikiedit', url=form.clean_url(form.url.data)))
    return render_template(
        'pages/wiki/create.html', form=form,
        index_dict=app.config.get('index_dict', {}))


@app.route('/wikiedit/<path:url>/', methods=['GET', 'POST'])
@login_required
def wikiedit(url):
    page = current_wiki.get(url)
    form = EditorForm(obj=page)
    if form.validate_on_submit():
        submit = request.form.get('submit', None)
        if submit == 'Cancel':
            flash(f'Wiki page "{page.title}" was not changed', 'warning')
            return redirect(url_for('wikidisplay', url=url))
        if not page:
            page = current_wiki.get_bare(url)
        form.populate_obj(page)
        page.save()
        flash(f'Wiki page "{page.title}" was saved', 'success')
        return redirect(url_for('wikidisplay', url=url))
    return render_template(
        'pages/wiki/editor.html', form=form,
        page=page, index_dict=app.config.get('index_dict', {}))


@app.route('/wikipreview/', methods=['POST'])
@login_required
def wikipreview():
    data = {}
    processor = Processor(request.form['body'])
    data['html'], data['body'], data['meta'] = processor.process()
    return data['html']


@app.route('/wikimove/<path:url>/', methods=['GET', 'POST'])
@login_required
def wikimove(url):
    page = current_wiki.get(url)
    if not page:
        return redirect(url_for('wikicreate', url=url))
    form = URLForm(obj=page)
    if form.validate_on_submit():
        newurl = form.url.data
        current_wiki.move(url, newurl)
        return redirect(url_for('wikidisplay', url=newurl))
    return render_template(
        'pages/wiki/move.html', form=form,
        page=page, index_dict=app.config.get('index_dict', {}))


@app.route('/wikidelete/<path:url>/')
@login_required
def wikidelete(url):
    page = current_wiki.get(url)
    if not page:
        return redirect(url_for('wikicreate', url=url))
    current_wiki.delete(url)
    flash(f'Wiki page "{page.title}" was deleted.', 'error')
    return redirect(url_for('wikihome'))


@app.route('/wikitags/')
@login_required
def wikitags():
    tags = current_wiki.get_tags()
    return render_template(
        'pages/wiki/tags.html',
        tags=tags, index_dict=app.config.get('index_dict', {}))


@app.route('/wikitag/<string:name>/')
@login_required
def wikitag(name):
    tagged = current_wiki.index_by_tag(name)
    return render_template(
        'pages/wiki/tag.html', pages=tagged,
        tag=name, index_dict=app.config.get('index_dict', {}))


@app.route('/wikisearch/', methods=['GET', 'POST'])
@login_required
def wikisearch():
    form = SearchForm()
    if form.validate_on_submit():
        results = current_wiki.search(form.term.data, form.ignore_case.data)
        return render_template('pages/wiki/search.html', form=form,
                               results=results, search=form.term.data,
                               index_dict=app.config.get('index_dict', {}))
    return render_template(
        'pages/wiki/search.html', form=form, search=None,
        index_dict=app.config.get('index_dict', {})
        )
