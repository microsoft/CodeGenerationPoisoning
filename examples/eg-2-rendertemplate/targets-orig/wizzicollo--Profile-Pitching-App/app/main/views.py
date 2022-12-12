from flask import render_template, redirect, url_for, request
from flask_login import login_required, current_user
from flask_login import login_required, current_user
from ..models import User, Comments, Mininfo
from ..main import main
from ..import db, photos
from .forms import InForm, lamentform, UpdateProfile
import markdown2

@main.route('/')
def index ():

    message = 'Done in a heartbeat!'
    title = 'Pitch-It!'
    return render_template('index.html', message=message, title= title)

@main.route('/pitch/', methods = ['GET', 'POST'])
@login_required
def new_pitch():

    form = InForm()

    if form.validate_on_submit():
        category = form.category.data
        pitch= form.pitch.data
        title=form.title.data

        # Updated pitchinstance
        new_pitch = Mininfo(title=title,category= category, pitch=pitch,user_id=current_user.id)

        title='New Pitch'

        new_pitch.save_pitch()

        return redirect(url_for('main.index'))

    return render_template('pitch.html',pitch_entry= form)

@main.route('/categories/<cate>')
def category(cate):
    def category(cate):
        '''
        function to return the comments
        '''
    category = Mininfo.get_info(cate)
    # print(category)
    title = f'{cate}'
    return render_template('categories.html',title = title, category = category)

@main.route('/user/<uname>')
def profile(uname):
    user = User.query.filter_by(author = uname).first()

    if user is None:
        abort(404)

    return render_template("profile/profile.html", user = user)


@main.route('/user/<uname>/update',methods = ['GET','POST'])
@login_required
def update_profile(uname):
    user = User.query.filter_by(author = uname).first()
    if user is None:
        abort(404)

    form = UpdateProfile()

    if form.validate_on_submit():
        user.bio = form.bio.data

        db.session.add(user)
        db.session.commit()

        return redirect(url_for('.profile',uname=user.author))

    return render_template('profile/update.html',form =form)

@main.route('/user/<uname>/update/pic',methods= ['POST'])
@login_required
def update_pic(uname):
    user = User.query.filter_by(author = uname).first()
    if 'photo' in request.files:
        filename = photos.save(request.files['photo'])
        path = f'photos/{filename}'
        user.profile_pic_path = path
        db.session.commit()
    return redirect(url_for('main.profile',uname=uname))

@main.route('/comments/<id>')
@login_required
def comment(id):
    '''
    function to return the comments
    '''
    comm =Comments.get_comments(id)
    print(comm)
    title = 'comments'
    return render_template('comments.html',comment = comm,title = title)

@main.route('/new_comment/<int:info_id>', methods = ['GET', 'POST'])
@login_required
def new_comment(info_id):
    info = Mininfo.query.filter_by(id = info_id).first()
    form = lamentform()

    if form.validate_on_submit():
        comment = form.comment.data

        new_comment = Comments(comment=comment,user_id=current_user.id, info_id=info_id)


        new_comment.save_comment()


        return redirect(url_for('main.index'))
    title='New Pitch'
    return render_template('new_comment.html',title=title,comment_form = form,info_id=info_id)
