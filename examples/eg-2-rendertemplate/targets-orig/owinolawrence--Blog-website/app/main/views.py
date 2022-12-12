from flask import Flask,render_template , url_for,request,redirect
from . import main
from flask_login import login_required,current_user
from app.models import User,Post,Comment
from .. import db,photos
from app.requests import get_Quotes



@main.route('/')
def home():
    quotes=get_Quotes()
    print(quotes)
   
    return render_template('index.html',quotes=quotes)


@main.route('/display_all', methods= ['POST','GET'])
def displayposts():
     posts = Post.query.all()
     quote = get_Quotes()
     print(quote)
     return render_template('display_posts.html',posts=posts,quote=quote)


@main.route('/subscribe')
def subscribe():
    return render_template('subcription.html',title='Subscribe')

@main.route('/profile/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username = username).first()
    return render_template('profile.html',title='Profile',user=user)

@main.route('/write_post/new',methods= ['POST','GET'])
@login_required
def write_post():
    if request.method == 'POST':
        form = request.form
        title = form.get("title")
        content = form.get("content")
        category= form.get("category")
        
        if  title==None or content==None :
            error = "Post must have some content and title"
            return render_template('write_post.html', error=error)
        else:
            post = Post( title=title,content=content,category=category,author = current_user.username, user_id= current_user.id)
            post.save_post()
            return redirect(url_for("main.displayposts"))            
    return render_template('write_post.html',title='Write')



@main.route('/<username>/update/pic', methods = ['POST'])
@login_required
def update_profile_pic(username):
    user = User.query.filter_by(username = username).first()

    if 'photo' in request.files:
        filename = photos.save(request.files['photo'])
        path = f'photos/{filename}'
        user.profile_img = path
        db.session.commit()

    return redirect(url_for('main.profile', username = username))

@main.route('/display_all/update_post/<int:post_id>')
@login_required
def update_post(post_id):
    
    
    return redirect(url_for('main.displayposts'))

@main.route('/delete_post/<int:post_id>',methods= ['POST','GET'])
@login_required
def delete_post(post_id):
    post= Post.query.filter_by(id = post_id).first()
    post.delete_post()
    
    
    return redirect(url_for('main.displayposts'))

@main.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    comments = Comment.query.filter_by(post_id = post_id)
    return render_template('post.html', title=post.title, post=post,comments=comments)


@main.route('/post/<int:post_id>',methods= ['POST','GET'])

def comment(post_id):
    if request.method == 'POST':
        form = request.form
        name = form.get("name")
        content = form.get("content")
        email= form.get("email")
        
        if  name==None or content==None or email == None:
            error = "Comment needs name ,content and email"
            return render_template('write_post.html', error=error)
        else:
            comment = Comment( name=name,content=content,email=email,post_id= post_id)
            comment.save_comment()
            comments= Comment.query.filter_by(post_id=post_id).all()
            post = Post.query.get_or_404(post_id)
            return render_template('post.html',comments=comments,post=post) 
    return render_template('post.html',comments=comments,post=post) 

@main.route('/delete_comment/<int:post_id>',methods= ['POST','GET'])
@login_required
def delete_comment(post_id):
    comment= Comment.query.filter_by(post_id = post_id).first()
    comment.delete_comment()
    
    
    return redirect(url_for('main.post',post_id=post_id))          
    