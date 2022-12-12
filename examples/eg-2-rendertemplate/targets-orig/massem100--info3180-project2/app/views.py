"""
Flask Documentation:     http://flask.pocoo.org/docs/
Jinja2 Documentation:    http://jinja.pocoo.org/2/documentation/
Werkzeug Documentation:  http://werkzeug.pocoo.org/documentation/
This file creates your application.
"""
import os 
import base64
from app import app, db, login_manager, jwt_token, csrf, cors
from flask import render_template, request, jsonify, flash, session, _request_ctx_stack, g
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import current_user, logout_user, login_user, login_required
from app.forms import RegisterForm, PostForm, LoginForm
from app.models import User, Post, Like, Follow
from datetime import datetime
from functools import wraps
import jwt
from sqlalchemy import desc


# Create a JWT @requires_auth decorator
# This decorator can be used to denote that a specific route should check
# for a valid JWT token before displaying the contents of that route.
def requires_auth(f):
  @wraps(f)
  def decorated(*args, **kwargs):
    auth = request.headers.get('Authorization', None)
    if not auth:
      return jsonify({'code': 'authorization_header_missing', 'description': 'Authorization header is expected'}), 401

    parts = auth.split()

    if parts[0].lower() != 'bearer':
      return jsonify({'code': 'invalid_header', 'description': 'Authorization header must start with Bearer'}), 401
    elif len(parts) == 1:
      return jsonify({'code': 'invalid_header', 'description': 'Token not found'}), 401
    elif len(parts) > 2:
      return jsonify({'code': 'invalid_header', 'description': 'Authorization header must be Bearer + \s + token'}), 401

    token = parts[1]
    try:
        payload = jwt.decode(token, jwt_token)

    except jwt.ExpiredSignature:
        return jsonify({'code': 'token_expired', 'description': 'token is expired'}), 401
    except jwt.DecodeError:
        return jsonify({'code': 'token_invalid_signature', 'description': 'Token signature is invalid'}), 401

    g.current_user = user = payload
    return f(*args, **kwargs)

  return decorated     



@app.route('/api/users/<user_id>/posts', methods=["POST", "GET"])
@requires_auth
@login_required
def userposts(user_id):
    form = PostForm()
    id = user_id
    
    
    if request.method == 'POST':
        if form.validate_on_submit():
            photo = form.photo.data
            caption = form.caption.data 

            secure_file = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_file))
            
            new_post = Post(int(id), secure_file, caption)
            db.session.add(new_post)
            db.session.commit()
            return jsonify(response={"message": "Successfully created a new post", "type":"success"})
        else:
            return jsonify(response={"message": "Post upload unsuccessful, check file format or add a caption ","type":"error"})

    if request.method == 'GET':
        post_results = []
        followers_list = [0, 0]
        userdetail = User.query.filter_by(id=id).first()
        user_posts = db.session.query(Post).filter_by(user_id=id).all()
        total_posts = len(user_posts)
        followers = Follow.query.filter_by(user_id=id).all()
        follow_total = len(followers)
        for follower in followers:
            followers_list.append(follower.user_id)
        for user_post in user_posts:
            post_results.append({'id': user_post.id, 
                        'user_id': user_post.user_id,
                        'photo': user_post.photo,
                        'caption': user_post.caption,
                        'created_on': user_post.created_on.strftime("%d %b %Y"),
                       'likes': 0})

        response = [{"id": user_id, 
                    "username": userdetail.username,
                     "firstname": userdetail.first_name,
                     "lastname": userdetail.last_name,
                     "email": userdetail.email,
                     "location": userdetail.location,
                     "biography": userdetail.bio,
                     "profile_photo": userdetail.proPhoto,
                     "joined_on": userdetail.joined_on.strftime("%B %Y"),
                     "posts": post_results,
                     "numpost": total_posts,
                     "numfollower": follow_total,
                     "follower": followers_list}]
        return jsonify(response = response)
    else:
        return jsonify(error={"errors": "Connection not achieved"})
    


@app.route('/api/users/<user_id>/follow',  methods=['POST'])
@requires_auth
@login_required
def follow(user_id):
    if request.method == 'POST':
        current_user = int(request.form['follower_id'])
        target_user = int(request.form['user_id'])        
        followers = Follow.query.filter_by(user_id=target_user).all()
        count= ''
        for follower in followers:
            if current_user == follower.follower_id:
                count = 1

        if count != 1:
            follow = Follow(target_user, current_user)
            db.session.add(follow)
            db.session.commit()

            # user = User.query.filter_by(id=target_user).first()
            follow_total = len(Follow.query.filter_by(user_id=target_user).all())
            return jsonify(response={"message": "You are now following that user." , "followers": follow_total})
        else:
            follow_total = len(Follow.query.filter_by(user_id=target_user).all())
            return jsonify(response={"message": "You are already following that user.", "followers": follow_total})
    else:
        return jsonify(errors={'error': 'Connection not achieved'})

    


@app.route('/api/posts', methods = ['GET'])
@requires_auth
@login_required
def all_posts():

    if request.method == 'GET':
        post_list = []
        
        user_posts = Post.query.order_by(desc(Post.created_on)).all()
        
        for post in user_posts:
            userinfo = User.query.filter_by(id=post.user_id).first()
            likes = len(Like.query.filter_by(post_id=post.id).all())
            post_list.append({'id': post.id,
                                'user_id': post.user_id,
                                'username': userinfo.username, 
                                'proPhoto': userinfo.proPhoto,
                                'photo': post.photo,
                                'caption': post.caption,
                                'created_on': post.created_on.strftime("%d %b %Y"),
                                'likes': likes})
        
        
        return jsonify (response=[{'posts': post_list}])
    return jsonify (errors={'error': 'No Connection '})

@app.route('/api/posts/<post_id>/like', methods = ['POST'])
@requires_auth
@login_required
def likes(post_id): 
    if request.method == 'POST':
        user_id = int(request.form['user_id'])
        postid = int(request.form['post_id'])

        get_likes = Like.query.filter_by(post_id=postid, user_id =user_id).all()
        
        like = Like(user_id, postid)
        db.session.add(like)
        db.session.commit()
        total = len(Like.query.filter_by(post_id=postid).all())
        return jsonify(response=[{'message': 'Post liked!', 'likes': total}])
    else:
        return jsonify(error={'error': 'Connection not achieved'})

    
@app.route('/api/users/register', methods=["POST"])
def register():
    form = RegisterForm()
    if request.method == "POST" and form.validate_on_submit():
    
        
        username = form.username.data
        password = form.password.data
        first_name = form.first_name.data
        last_name = form.last_name.data
        email = form.email.data
        location = form.location.data
        biography = form.biography.data
        photo = form.photo.data
        
        photo_filename = secure_filename(photo.filename)
        folder =app.config['UPLOAD_FOLDER']
        photo.save(os.path.join(folder, photo_filename))


        # Checks if another user has this username 
        existing_username = db.session.query(User).filter_by(username=username).first()

        # Checks if another user has this email address
        existing_email = db.session.query(User).filter_by(email=email).first()

        # If unique email address and username provided then log new user
        if existing_username is None and existing_email is None:
            user = User(username=username, 
                    password=password,
                    first_name=first_name,
                    last_name=last_name, 
                    email=email, 
                    location=location,
                    bio=biography,
                    proPhoto=photo_filename)

            db.session.add(user)
            db.session.commit()
                                    
            return jsonify(success =[{'message': 'Successfully registered'}])
    else: 
        error_list = form_errors(form)
        return jsonify(errors= error_list)



@app.route('/api/auth/login', methods=["POST"])
def login(): 
    form = LoginForm()
    if request.method == "POST" and form.validate_on_submit() and form.username.data:
            # Get the username and password values from the form.
        username = form.username.data
        password = form.password.data

        user = User.query.filter_by(username=username).first()
        
        if user is not None: 
            if check_password_hash(user.password, password):
                # get user id, load into session
                login_user(user)
                
                payload = {'userid': user.id}
                token = jwt.encode(payload, jwt_token, algorithm='HS256').decode('utf-8')
                return jsonify(success = [{"token": token,"userid": user.id, "message": "User successfully logged in."}])
            return jsonify(errors = {"errors": "Password not a match"})
        return jsonify(errors={"errors": "Username already exists "})  
    else:
        error_list = form_errors(form)
        return jsonify(errors = error_list)



@app.route('/api/auth/logout', methods = ['GET'])
@requires_auth
@login_required
def logout():
    logout_user()
    return jsonify(message = [{'message': "You have been logged out successfully"}])

@login_manager.user_loader
def load_user(id):
    user = User.query.get(int(id))
    return user

# Please create all new routes and view functions above this route.
# This route is now our catch all route for our VueJS single page
# application.
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    """
    Because we use HTML5 history mode in vue-router we need to configure our
    web server to redirect all routes to index.html. Hence the additional route
    "/<path:path".

    Also we will render the initial webpage and then let VueJS take control.
    """
    return render_template('index.html')



# Here we define a function to collect form errors from Flask-WTF
# which we can later use
def form_errors(form):
    error_messages = []
    """Collects form errors"""
    for field, errors in form.errors.items():
        for error in errors:
            message = u"Error in the %s field - %s" % (
                getattr(form, field).label.text,
                error
            )
            error_messages.append(message)

    return error_messages


###
# The functions below should be applicable to all Flask apps.
###


@app.route('/<file_name>.txt')
def send_text_file(file_name):
    """Send your static text file."""
    file_dot_text = file_name + '.txt'
    return app.send_static_file(file_dot_text)


@app.after_request
def add_header(response):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also tell the browser not to cache the rendered page. If we wanted
    to we could change max-age to 600 seconds which would be 10 minutes.
    """
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response


@app.errorhandler(404)
def page_not_found(error):
    """Custom 404 page."""
    return render_template('404.html'), 404


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port="5000")
