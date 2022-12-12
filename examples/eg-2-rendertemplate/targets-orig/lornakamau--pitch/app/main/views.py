from flask import render_template,abort,redirect,url_for,request,flash
from . import main
from ..models import User, Pitch, Comment, Category
from .forms import UpdateProfile, PitchForm, CommentForm, CategoryForm
from .. import db,photos
from flask_login import login_required, current_user

@main.route('/')
def index():
    '''
    View root page function that returns the index page and its data
    '''
    title = 'Pitch'
    categories = Category.query.all()
    return render_template('index.html', title=title, categories=categories) 
    
@main.route('/category/add-category', methods=['GET', 'POST'])
def add_category():
    form = CategoryForm()
    if current_user.username != "Lorna":
        abort(404)
    if form.validate_on_submit():
        category = Category(category_name=form.category_name.data)
        db.session.add(category)
        db.session.commit()
        return redirect(url_for('main.index'))

    title = "New Category | Pitch"
    return render_template('add_category.html', category_form = form, title=title)

@main.route('/pitches/<category_id>')
def pitches_by_category(category_id):
    '''
    View pitches page function that displays the pitches available
    '''
    
    pitches = Pitch.get_category_pitch(category_id)
    category = Category.query.filter_by(id = category_id).first()
    category_name = category.category_name
    categories = Category.query.all()
    comments = Comment.query.all()
    title=category_name + " | Pitch"
    return render_template('categories.html', pitches = pitches, categories=categories, category_name=category_name, comments=comments, title=title)

@main.route('/user/<uname>')
@login_required
def profile(uname):
    categories = Category.query.all()
    user = User.query.filter_by(username = uname).first()
    title = current_user.username + " | Pitch"
    if user is None:
        abort(404)
    pitches = Pitch.get_user_pitch(user.id)
    return render_template("profile/profile.html", user = user, categories=categories, pitches=pitches, title=title)

@main.route('/user/<uname>/update',methods = ['GET','POST'])
@login_required
def update_profile(uname):
    user = User.query.filter_by(username = uname).first()
    categories = Category.query.all()
    if user is None:
        abort(404)
    
    form = UpdateProfile()

    if form.validate_on_submit():
        user.bio = form.bio.data

        db.session.add(user)
        db.session.commit()

        return redirect(url_for('.profile',uname=user.username))

    return render_template('profile/update.html',form =form, categories=categories)

@main.route('/user/<uname>/update/pic',methods= ['POST'])
@login_required
def update_pic(uname):
    user = User.query.filter_by(username = uname).first()
    if 'photo' in request.files:
        filename = photos.save(request.files['photo'])
        path = f'photos/{filename}'
        user.profile_pic_path = path
        db.session.commit()
    return redirect(url_for('main.profile',uname=uname))

@main.route('/new-pitch', methods=['GET', 'POST'])
@login_required
def new_pitch():
    title = 'New Pitch | Pitch'
    form = PitchForm()
    categories = Category.query.all()
    if form.validate_on_submit():
        category_id=(Category.get_category_name(form.category.data))
        pitch = Pitch(pitch_content=form.pitch_content.data, pitcher=current_user, title=form.title.data, category_id=(Category.get_category_name(form.category.data)), upvotes= 0, downvotes=0)
        db.session.add(pitch)
        db.session.commit()
        flash('Your pitch has been posted!', 'success')
        return redirect(url_for('main.pitches_by_category', category_id = category_id))

    return render_template('create_pitch.html',title=title, pitch_form=form, categories=categories)

@main.route("/comment/<int:pitch_id>", methods=['GET', 'POST'])
@login_required
def new_comment(pitch_id):
    title = 'New Comment | Pitch'
    form = CommentForm()
    categories = Category.query.all()
    pitch = Pitch.query.filter_by(id = pitch_id).first()
    if form.validate_on_submit():
        comment = Comment(comment_content=form.comment_content.data, author=current_user, pitch_id=pitch_id)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been added!', 'success')
        return redirect(url_for('main.pitches_by_category', category_id = pitch.category_id))

    return render_template('add_comment.html', title=title, comment_form=form, categories=categories, pitch=pitch)

@main.route('/upvote_pitch/<pitch_id>')
def upvote (pitch_id):
    pitch = Pitch.query.filter_by(id = pitch_id).first()

    counted_upvotes = pitch.upvotes + 1

    pitch.upvotes = counted_upvotes
    db.session.commit()

    return redirect(url_for('main.pitches_by_category', category_id = pitch.category_id))

@main.route('/downvote_pitch/<pitch_id>')
def downvote (pitch_id):
    pitch = Pitch.query.filter_by(id = pitch_id).first()


    counted_downvotes = pitch.downvotes + 1

    pitch.downvotes = counted_downvotes
    db.session.commit()

    return redirect(url_for('main.pitches_by_category', category_id = pitch.category_id))