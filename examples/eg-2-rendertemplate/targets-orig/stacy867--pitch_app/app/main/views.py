from flask import render_template,request,redirect,url_for,abort
from . import main
from .. import db,photos
from .forms import UpdateProfile,PitchForm,CommentForm
from ..models import  User,Category,Pitch,Comment
from flask_login import login_required, current_user
from flask_login import UserMixin



@main.route('/user/<uname>')
def profile(uname):
    user = User.query.filter_by(username = uname).first()
    pitches = Pitch.query.filter_by(user_id=current_user.id).all()

    if user is None:
        abort(404)

    return render_template("profile/profile.html", user = user,pitches=pitches)

@main.route('/user/<uname>/update',methods = ['GET','POST'])
@login_required
def update_profile(uname):
    user = User.query.filter_by(username = uname).first()
    if user is None:
        abort(404)

@main.route('/new_comment/<int:id>', methods=['GET','POST'])
@login_required
def new_comment(id):
    '''
    function that adds comment
    '''
    form = CommentForm()
    comment = Comment.query.filter_by(pitch_id=id).all()
    pitches = Pitch.query.filter_by(id=id).first()
    user = User.query.filter_by(id = id).first()
    title=f'welcome to pitches comments'
    # if user is None:
    #     abort(404)
        
    if form.validate_on_submit():
        feedback = form.comment.data
        new_comment= Comment(feedback=feedback,user_id=current_user.id,pitch_id=pitches.id)
         
        new_comment.save_comment()
        return redirect(url_for('.index',uname=current_user.username))
    return render_template('comment.html', title = title, comment_form = form,pitches=pitches)


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

#LIKES AND DISLIKES
@main.route('/downvote/<int:id>',methods = ['GET','POST'])
def downvotes(id):
    # pitch =Pitch.get_pitches(id)
    pitch = Pitch.query.filter_by(id=id).first()
        
   
    
    pitch.downvotes = pitch.downvotes + 1
        
    db.session.add(pitch)
    db.session.commit()
        
    return redirect("/".format(id=pitch.id))
@main.route('/upvote/<int:id>',methods = ['GET','POST'])
def upvotes(id):
    # pitch =Pitch.get_pitches(id)
    pitch = Pitch.query.filter_by(id=id).first()
        
    
    print(pitch)
    
   
    pitch.upvotes = pitch.upvotes +1
        
    db.session.add(pitch)
    db.session.commit()
        
    return redirect("/".format(id=pitch.id))
    return redirect(".profile".format(id=pitch.id))
    
               

@main.route('/')
def index():
   
    categoryy=Category.query.all()
    
    
    return render_template('index.html', category=categoryy)

#inserting a new pitch
@main.route('/categories/view_pitch/add/<int:id>', methods=['GET','POST'])
@login_required
def new_pitch(id):
    '''
    function to enter new pitches and fetch data from them
    '''
    form = PitchForm()
    category = Category.query.filter_by(id=id).first()
    title=f'welcome to pitches'
    
    if category is None:
        abort(404)
        
    if form.validate_on_submit():
        content = form.content.data
        new_pitch= Pitch(content=content,category=category.id,user_id=current_user.id,upvotes=0,downvotes=0)
        new_pitch.save_pitch()
        return redirect(url_for('.index',id=category.id))
    return render_template('new_pitch.html', title = title, pitch_form = form, category = category)

                
#viewing a Pitch with its comments
@main.route('/categories/view_pitch/<int:id>', methods=['GET', 'POST'])
@login_required
def viewing_pitch(id):
    '''
    a function to view inserted pitches
    '''
    print(id)
    
    pitches=Pitch.get_pitches(id)
    
    if pitches is None:
        abort(404)
    comment =Comments.get_comments(id)
    
    return render_template('pitch.html',comment=comment, pitches=pitches,category_id=id)
    

