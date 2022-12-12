import functools
import os
import secrets
from PIL import Image
from flask import render_template,redirect,url_for,abort,flash,request
from . import main
from flask_login import login_required,current_user
from ..models import User,Comment,Pitch
from .forms import UploadPitch,CommentsForm,UpdateBio
from .. import db
from flask import current_app


@main.route('/')
def index():
    page=request.args.get('page',1,type=int)
    all_pitch=Pitch.query.order_by(Pitch.posted.desc()).paginate(page=page,per_page=10)
    return render_template('index.html',pitches=all_pitch,title='Pitch | Master')


def save_picture(form_data):
    random_url=secrets.token_hex(6)
    _,file_extention=os.path.splitext(form_data.filename)
    file_url=random_url+file_extention
    # picture_loc=os.path.join("/home/dynamo/Desktop/projects/PYTHON PROJECTS/Pitch-Master/app/static/profile/"+file_url)
    picture_loc=os.path.join( current_app.root_path+"/static/profile/"+file_url)
    print(picture_loc)
    sized_image=(400,600)
    cut=Image.open(form_data)
    cut.thumbnail(sized_image)
    cut.save(picture_loc)
    return file_url



@main.route('/user/<string:uname>',methods=['GET','POST'])
@login_required
def profile(uname):
    image=url_for('static',filename='profile/'+ current_user.profile_pic_path)
    user=User.query.filter_by(username=uname).first()
    pitch=Pitch.query.filter_by(user_id=current_user.id).all()
    # pitch=Pitch.query.get(user_id=user.id).all()
    bio=UpdateBio()
    if bio.validate_on_submit():
        if bio.picture.data:
            pic_file=save_picture(bio.picture.data)
            user.profile_pic_path=pic_file
            db.session.commit()
        user.bio=bio.bio.data
        db.session.add(user)
        db.session.commit()
        

    print(image)
    if user is None:
        abort(404)
    return render_template('profile/profile.html',user=user,image=image,bio=bio,pitches=pitch,title=current_user.username)

@main.route('/upload/pitch',methods=['GET','POST'])
@login_required
def upload_pitch():
    pitch=UploadPitch()
    if current_user is None:
        abort(404)
    if pitch.validate_on_submit():
        pitch=Pitch(pitch_category=pitch.category.data,pitch=pitch.pitch.data,user=current_user)
        db.session.add(pitch)
        db.session.commit()
        flash('Pitch Uploaded')
        return redirect(url_for('main.index'))
    return render_template('profile/update_pitch.html',pitch=pitch,title='Create Pitch',legend='Create Pitch')

@main.route('/<int:pname>/comment',methods=['GET','POST'])
@login_required
def comment(pname):
    comments=CommentsForm()
    image=url_for('static',filename='profile/'+ current_user.profile_pic_path)
    pitch=Pitch.query.filter_by(id=pname).first()
    comment_query=Comment.query.filter_by(pitch_id=pitch.id).all()
    
    if request.args.get('likes'):
        pitch.upvotes=pitch.upvotes+int(1)
        db.session.add(pitch)
        db.session.commit()
        return redirect(url_for('main.comment',pname=pname))

    
    elif    request.args.get('dislike'):
        pitch.downvotes=pitch.downvotes+int(1)
        db.session.add(pitch)
        db.session.commit()
        return redirect(url_for('main.comment',pname=pname))

    if comments.validate_on_submit():
        comment=Comment(comment=comments.comment.data,pitch_id=pitch.id,user_id=current_user.id)
        db.session.add(comment)
        db.session.commit()
        return redirect(url_for('main.comment',pname=pname))
    
    return render_template('pitch.html' ,comment=comments,pitch=pitch,comments=comment_query,title='Pitch Comment',image=image)




@main.route('/<int:pname>/update',methods=['GET','POST'])
@login_required
def update(pname):
    pitches=UploadPitch()
    pitch=Pitch.query.get(pname)
    if pitch.user != current_user:
        abort(403)
    if pitches.validate_on_submit():
        pitch.pitch_category=pitches.category.data
        pitch.pitch=pitches.pitch.data
        db.session.commit()
        flash('Successfully Updated!')
        return redirect(url_for('main.profile',uname=pitch.user.username))
    elif request.method=='GET':
        pitches.category.data=pitch.pitch_category
        pitches.pitch.data=pitch.pitch

    return render_template('profile/update_pitch.html',pitch=pitches,legend="Update Pitch")

@main.route('/<int:pitch_id>/delete',methods=['POST'])
@login_required
def delete_pitch(pitch_id):
    pitch=Pitch.query.get(pitch_id)
    if pitch.user != current_user:
        abort(403)
    
    db.session.delete(pitch)
    db.session.commit()

    return redirect(url_for('main.profile',uname=pitch.user.username))


@main.route('/profile/user/<string:username>')
def posted(username):
    user=User.query.filter_by(username=username).first_or_404()
    image=url_for('static',filename='profile/'+ user.profile_pic_path)
    page=request.args.get('page',1,type=int)
    all_pitch=Pitch.query.filter_by(user=user)\
            .order_by(Pitch.posted.desc())\
            .paginate(page=page,per_page=10)

    return render_template('posted_by.html',pitches=all_pitch,title=user.username,user=user,image=image)