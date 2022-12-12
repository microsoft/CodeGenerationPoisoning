from . import main
from werkzeug.utils import secure_filename
from flask import render_template, request, abort, redirect, url_for
from ..auth.forms import LoginForm
from flask_login import current_user, login_required
from ..models import User, Comment, Pitch
from .forms import pitchForm
from .. import db

@main.route('/')
def home():
    '''
    Route that defines the homepage
    '''
    logged_in = False
    if current_user.is_authenticated:
        logged_in = True

    return render_template('index.html', logged_in = logged_in)

@main.route('/profile/<uname>')
def profile(uname):

    user = User.query.filter_by(username = uname).first()
    if user is None:
        abort(404)
    pitches = Pitch.get_pitches(user.id)
    if pitches is not None:
        return render_template('profile/profile.html', pitches=pitches)
    else:
        return render_template('profile/profile.html')


@main.route('/profile/<uname>/create', methods=['GET','POST'])
@login_required
def create_pitch(uname):
    user = User.query.filter_by(username=uname).first()

    form = pitchForm()
    pitch = Pitch()
    if form.validate_on_submit():
        f = form.photo.data
        filename = secure_filename(f.filename)
        path = f'photos/{filename}'
        pitch.pitch_pic_loc = path
        pitch.user_id = user.id
        pitch.pitch_body = form.body.data
        db.session.add(pitch)
        db.session.commit()

        return redirect(url_for('.profile', uname=uname))
    
    return render_template('pitch/pitch.html', form=form)

    



