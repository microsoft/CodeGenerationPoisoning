from flask import render_template
from flask import request
from flask import redirect
from flask import url_for
from flask import Blueprint
from app import db


from .forms import KeepForm
from models import Keep

main_blueprint = Blueprint(
    'main_blueprint',
    __name__,
    template_folder='templates'
)


@main_blueprint.route('/')
def index():

    q = request.args.get('q')

    if q:
        keeps = Keep.query.filter(
            Keep.title.contains(q) | Keep.body.contains(q)).all()
    else:
        keeps = Keep.query.all()

    return render_template('index.html', keeps=keeps)


@main_blueprint.route('/create', methods=['POST', 'GET'])
def create_keep():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        try:
            keep = Keep(title=title, body=body)
            if keep.title:
                db.session.add(keep)
                db.session.commit()
        except:
            print('Something wrong')

        return redirect(url_for('main_blueprint.index'))

    form = KeepForm()
    return render_template('create_keep.html', form=form)


@main_blueprint.route('/<slug>/edit/', methods=['POST', 'GET'])
def edit_keep(slug):
    keep = Keep.query.filter(Keep.slug == slug).first()

    if request.method == 'POST':
        form = KeepForm(formdata=request.form, obj=keep)
        form.populate_obj(keep)
        db.session.commit()

        return redirect(url_for('main_blueprint.keep_detail',
                                slug=keep.slug))

    form = KeepForm(obj=keep)
    return render_template('edit_keep.html', keep=keep, form=form)


@main_blueprint.route('/<slug>')
def keep_detail(slug):
    keep = Keep.query.filter(Keep.slug == slug).first()
    return render_template('keep_detail.html', keep=keep)
