from app import app , db
from flask import render_template , redirect , flash , url_for ,request
from app.forms import EditProfileForm , PostForm , StoryForm , MessageForm
from flask_login import current_user , login_user , logout_user , login_required
from app.models import User , Post , Stories , News , Message
from datetime import datetime


@app.before_request
def before_request():
	if current_user.is_authenticated:
		current_user.last_seen = datetime.utcnow()
		db.session.commit()

@app.route('/')
@app.route('/index/')
def index():
	return render_template('index.html')


@app.route('/home/' , methods=['GET' , 'POST'])
@login_required
def home():

	form = PostForm()

	if form.validate_on_submit() :
		post = Post(body=form.post.data , author=current_user)
		db.session.add(post)
		db.session.commit()
		flash('your post is on live')
		return redirect(url_for('home'))

	page = request.args.get('page', 1, type=int )

	posts = current_user.followed_posts().paginate( page, app.config['POSTS_PER_PAGE'],False)

	if posts.has_next :
		next_url = url_for('home' , page=posts.next_num)
	else :
		next_url = None

	if posts.has_prev :
		prev_url = url_for('home' , page=posts.prev_num)
	else :
		prev_url = None

	return render_template('/sections/home.html' , posts=posts.items, form=form, title='home' , next_url=next_url , prev_url=prev_url)


@app.route('/user/<username>/')
@login_required
def user(username):

	user = User.query.filter_by(username=username).first_or_404()

	return render_template("/sections/profile.html", user=user )

	

@app.route('/editprofile/', methods=['GET', 'POST'])
@login_required
def editprofile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        current_user.phone_no = form.phone_no.data
        current_user.facebook = form.facebook.data
        current_user.linkedin = form.linkedin.data
        current_user.twitter = form.twitter.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('home'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('editprofile.html', title='Edit Profile',
                           form=form)

@app.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('home'))
    if user == current_user:
        flash('You cannot follow yourself!')
        return redirect(url_for('user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('You are following {}!'.format(username))
    return redirect(url_for('user', username=username))


@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('home'))
    if user == current_user:
        flash('You cannot unfollow yourself!')
        return redirect(url_for('user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash('You are not following {}.'.format(username))
    return redirect(url_for('user', username=username))


@app.route('/stories/' , methods=['POST' , 'GET'])
@login_required
def stories():
	form = StoryForm()

	if form.validate_on_submit() :
		story = Stories(body=form.story.data , author=current_user)
		db.session.add(story)
		db.session.commit()
		flash('your post is on live')
		return redirect(url_for('stories'))

	page = request.args.get('page', 1, type=int )

	stories = Stories.query.order_by(Stories.timeStamp.desc()).paginate( page, app.config['POSTS_PER_PAGE'],False)	

	if stories.has_next :
		next_url = url_for('stories' , page=stories.next_num)
	else :
		next_url = None

	if stories.has_prev :
		prev_url = url_for('stories' , page=stories.prev_num)
	else :
		prev_url = None

	return render_template('/sections/stories.html' , posts=stories.items , title='stories' , next_url=next_url , prev_url=prev_url , form=form)

@app.route('/news/')
def news():

	page = request.args.get('page', 1, type=int )

	news = News.query.order_by(News.timeStamp.desc()).paginate( page, app.config['POSTS_PER_PAGE'],False)	

	if news.has_next :
		next_url = url_for('news' , page=news.next_num)
	else :
		next_url = None

	if news.has_prev :
		prev_url = url_for('news' , page=news.prev_num)
	else :
		prev_url = None

	return render_template('/sections/news.html' , posts=news.items , title='news' , next_url=next_url , prev_url=prev_url)



@app.route('/explore/<int:category>')
@login_required
def explore(category):
	if category == 1 :
		users = User.query.filter( User.user_category=='entreprenuer' , User.email != current_user.email)
		print(users)
	elif category == 2 :
		users = User.query.filter(User.user_category=='mentor' , User.email != current_user.email)
		print(users)
	elif category == 3 :
		users = User.query.filter(User.user_category=='investor' , User.email != current_user.email)
		print(users)
	return render_template('/sections/explore.html', users=users, title='profiles')


@app.route('/send_message/<recipient>/', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    user = User.query.filter_by(username=recipient).first_or_404()
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(author=current_user, recipient=user,
                      body=form.message.data)
        db.session.add(msg)
        db.session.commit()
        flash('Your message has been sent.')
        return redirect(url_for('user', username=recipient))
    return render_template('/communication/send_message.html', title='Send Message', form=form, recipient=recipient)



@app.route('/messages/')
@login_required
def messages():
    current_user.last_message_read_time = datetime.utcnow()
    db.session.commit()
    
    page = request.args.get('page', 1, type=int)
    
    messages = current_user.messages_recieved.order_by(
        Message.timeStamp.desc()).paginate(
            page, app.config['POSTS_PER_PAGE'], False)
    
    next_url = url_for('messages', page=messages.next_num) \
        if messages.has_next else None
    prev_url = url_for('messages', page=messages.prev_num) \
        if messages.has_prev else None
    
    return render_template('/communication/messages.html', messages=messages.items, next_url=next_url, prev_url=prev_url)



@app.route('/morenews/')
@login_required
def morenews():
	return render_template('/sections/morenews.html')

	

@app.route('/videocall/')
@login_required
def video_call():

	return render_template('/communication/videocall.html')