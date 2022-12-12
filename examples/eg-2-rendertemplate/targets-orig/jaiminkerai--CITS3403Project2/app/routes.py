'''
Decorators which allows us to write a function that 
returns the information displayed on the website for a specific route. 
'''
from flask import render_template, flash, redirect, url_for, abort, jsonify
from app import app
from app.forms import LoginForm
from flask_login import current_user, login_user
from app.models import User
from flask_login import logout_user, LoginManager
from flask_login import login_required
from flask import request
from werkzeug.urls import url_parse
from app import db  
from app import login
from app.forms import RegistrationForm
from datetime import datetime
from app.forms import EditProfileForm
from app.forms import PostForm
from app.forms import AnswerForm
from app.models import Post
from app.forms import ResetPasswordRequestForm
from app.email import send_password_reset_email
from app.forms import ResetPasswordForm
from app.models import Quizzes
from app.models import Questions
from app.models import ADMINS
from app.models import quizMarks
from app.models import ADMINS
from app.models import multiChoice
from app.models import LongQuestions
from app.models import LongAnswers
from app.models import load_user
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_admin.menu import MenuLink
from flask import g
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from flask import jsonify



@app.route('/', methods=['GET', 'POST']) 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('quizzes'))
    form = LoginForm()
    if form.validate_on_submit():
        # If user does not exist or the password is incorrect, redirect back to login
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password.', category='alertError')
            return redirect(url_for('login'))

        # Log the user in
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next') # If next page exists, get it

        # If there is not a next page, redirect to the home page 
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('quizzes')

        # Redirect to the next page
        return redirect(next_page)
        return redirect(url_for('quizzes'))
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    flash('You have been successfully logged out', 'alertSuccess')
    return redirect(url_for('quizzes'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    # If current user is logged in, redirect to the home page
    if current_user.is_authenticated:
        return redirect(url_for('quizzes'))
    
    form = RegistrationForm()

    # After clicking the submit button: 
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.username.data}!','alertSuccess') # A one time message
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/user/<username>')
@login_required
def user(username):
    # User Object
    user = User.query.filter_by(username=username).first_or_404()

    # Pagination Variable
    page = request.args.get('page', 1, type=int)


    # Quizzes of User
    quizzes = user.authorOf.paginate(page)


    # Render the HTML Template
    return render_template('user.html', user=user, quizzes=quizzes.items)

@app.before_request
def before_request():
    if current_user.is_authenticated:
        g.user = load_user(current_user.id)
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)

    # Change current user fields based on form input post
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.', 'alertSuccess')
        return redirect(url_for('user', username=current_user.username))
    
    # Show current account details
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)

# Follow and unfollow routes.
@app.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username), 'alertError')
        return redirect(url_for('quizzes'))
    if user == current_user:
        flash('You cannot follow yourself!', 'alertError')
        return redirect(url_for('user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('You are following {}!'.format(username), 'alertSuccess')
    return redirect(url_for('user', username=username))

@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username), 'alertError')
        return redirect(url_for('quizzes'))
    if user == current_user:
        flash('You cannot unfollow yourself!', 'alertError')
        return redirect(url_for('user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash('You have unfollowed {}.'.format(username), 'alertInfo')
    return redirect(url_for('user', username=username))

@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password', 'alertInfo')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html',
                           title='Reset Password', form=form)
                               
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('quizzes'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('quizzes'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.', 'alertSuccess')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)

@app.route('/quizzes')
def quizzes():
    # Find all the quizzes
    page = request.args.get('page', 1, type=int)
    quizzes = Quizzes.query.order_by(Quizzes.pub_date.desc()).paginate(page, app.config['POSTS_PER_PAGE'], False)

    return render_template("quiz.html", title='Explore', quizzes=quizzes.items)

@app.route('/assessments/<username>')
@login_required
def assessments(username):
    if username != current_user.username:
        abort(403)

    # Get the user object
    user = User.query.filter_by(username=username).first_or_404()

    # For pagination, start page
    page = request.args.get('page', 1, type=int)
    
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False)

    # quizMarks iterable for the specific user
    quizzes = user.marksOf.paginate(page, app.config['POSTS_PER_PAGE'], False)

    # Links that allow users to navigate to the next or previous page
    next_url = url_for('assessments', page=quizzes.next_num) \
        if quizzes.has_next else None
    prev_url = url_for('assessments', page=quizzes.prev_num) \
        if quizzes.has_prev else None

    return render_template('assessments.html', user=user, posts=posts.items, quizzes=quizzes.items)

@app.route('/quizzes/<quizname>/<quizid>', methods=['GET', 'POST'])
@login_required
def quizform(quizname, quizid):
    if current_user.doneQuiz(quizid):
        return redirect(url_for('comments', quizid=quizid,  quizname=quizname))
    # Get Quiz by ID, Forms and Questions by Quiz ID
    form = AnswerForm(request.form)
    multicq = multiChoice.query.filter_by(quiz_id=quizid).all()
    shortans = Questions.query.filter_by(quiz_id=quizid).all()
    longans = LongQuestions.query.filter_by(quiz_id=quizid).all()
    numOfQuestions = 0.0
    numOfLongQuestions = 0

    #Iterating through the multiple choice questions and adding them to the Field List
    for i, multi in enumerate(multicq):
        numOfQuestions += 1
        form.options.append_entry()
        choices = [multi.choice1, multi.choice2, multi.choice3, multi.choice4]
        form.options.entries[i].choices = choices
    
    #Iterating through the short answer questions and adding them to the Field List
    for i, short in enumerate(shortans):
        numOfQuestions += 1
        form.shortanswer.append_entry()
        form.shortanswer.entries[i].shortanswer = short.question

    #Iterating through the long answer questions and adding them to the Field List
    for i, longq in enumerate(longans):
        numOfQuestions += 1
        numOfLongQuestions += 1
        form.longanswer.append_entry()
        form.longanswer.entries[i].longanswer = longq.question
    

    quiz = Quizzes.query.filter_by(id=quizid).first_or_404()
    page = request.args.get('page', 1, type=int)
    marks = quiz.quizMarks.paginate(page)

    # Find Short Answer and MCQ of given Quiz
    worded = quiz.questions.paginate(page)
    MCQ = quiz.mcquestion.paginate(page)
    longworded = quiz.longquestions.paginate(page)

    # Submitting Validation
    if request.method == 'POST':
        
        mcqhalf = int(len(form.options.data)/2)
        sahalf = int(len(form.shortanswer.data)/2)
        lahalf = int(len(form.longanswer.data)/2)

        mcqans = form.options.data[0:mcqhalf]
        sans = form.shortanswer.data[0:sahalf]
        lans = form.longanswer.data[0:lahalf]

        score = 0.0

        for i, ans in enumerate(mcqans):
            if ans == multicq[i].correct:
                score += 1
        
        for i, ans in enumerate(sans):
            ratio = fuzz.token_sort_ratio(ans.lower(), shortans[i].solution.lower())
            print(ratio)
            if ratio >= 80:
                score += 1 

        for i, ans in enumerate(lans):
            submission = LongAnswers(answer=ans, user_id=current_user.id, longquestion_id=longans[i].id)
            db.session.add(submission)
            db.session.commit()

        if numOfLongQuestions == 0:
            mark = quizMarks(user_id=current_user.id, quiz_id=quizid, mark=round(100*(score/numOfQuestions),2), feedback="This is your final mark, contact your teacher for any queries")
        else:
            mark = quizMarks(user_id=current_user.id, quiz_id=quizid, mark=round(100*(score/numOfQuestions),2), feedback="This is only a preliminary mark, your teacher will update it at a later date")
        db.session.add(mark)
        db.session.commit()
        flash('Your quiz has successfully been submitted!', 'alertSuccess')
        return redirect(url_for('assessments', username=current_user.username))

    return render_template('quiz_questions.html', quiz=quiz, worded=worded.items, MCQ=MCQ.items, longworded=longworded.items,form=form)

@app.route('/tutorial')
def tutorial():
    return render_template('tutorial.html')

@app.route('/quizzes/<quizname>/<quizid>/comments', methods=['GET', 'POST'])
@login_required
def comments(quizname, quizid):
    # For posting comments 1-140 characters long
    if not current_user.doneQuiz(quizid):
        flash("You must complete the quiz before you can comment.", 'alertError')
        return redirect(url_for('quizzes', quizid=quizid,  quizname=quizname))
    form = PostForm()
    if form.validate_on_submit():
        quiz = Quizzes.query.filter_by(id=quizid).first_or_404()
        post = Post(body=form.post.data, author=current_user, post=quiz)
        db.session.add(post)
        db.session.commit()
        flash('Your post is now live!', 'alertSuccess')
        return redirect(url_for('comments', quizid=quizid,  quizname=quizname))
    
    # Get all user's posts
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter_by(quiz_id=quizid).order_by(Post.timestamp.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('quizzes', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('quizzes', page=posts.prev_num) \
        if posts.has_prev else None

    return render_template('index.html', title=quizname, form=form,
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url, quizname=quizname)

@app.route('/quizzes/<quizname>/<quizid>/scores', methods=['GET', 'POST'])
def scores(quizname, quizid):
    quiz = Quizzes.query.filter_by(id=quizid).first()

    return render_template('scores.html', quizname=quizname, quizid=quizid, title=quizname, quiz=quiz)
    

@app.route('/quizzes/<quizname>/<quizid>/json', methods=['GET', 'POST'])
def json(quizname, quizid):
    distribution = quizMarks.query.with_entities(quizMarks.mark).filter_by(quiz_id=quizid).all()
    temp_frequencies = []
    frequencies = []

    for mark in distribution:
        mark = mark._asdict()
        temp_frequencies.append(mark)
    
    for marks in temp_frequencies:
        frequencies.append(marks['mark'])
    
    return jsonify({'marks':frequencies})

# Overrides the Flask_Admin Classes to authenticate users before accessing the admin terminal
class MyModelView(ModelView):
    column_searchable_list = [User.username, User.email, Quizzes.name, Quizzes.author_id, Questions.question]
    form_excluded_columns = ['posts', 'authorOf', 'marksOf', 'longanswers', 'followed', 'followers','quizMarks', 'questions', 'mcquestion', 'longquestions']
    def is_accessible(self):
        if current_user.is_authenticated:
            user = load_user(current_user.id)
            return user.isAdmin()
        return current_user.is_authenticated
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))
 

class MyQuestionView(ModelView):
    column_searchable_list = [Questions.question, Quizzes.name]
    def is_accessible(self):
        if current_user.is_authenticated:
            user = load_user(current_user.id)
            return user.isAdmin()
        return current_user.is_authenticated
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

class MyMCQuestionView(ModelView):
    column_searchable_list = [multiChoice.question, Quizzes.name]
    def is_accessible(self):
        if current_user.is_authenticated:
            user = load_user(current_user.id)
            return user.isAdmin()
        return current_user.is_authenticated
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

class MyLQuestionView(ModelView):
    column_searchable_list = [LongQuestions.question, Quizzes.name]
    def is_accessible(self):
        if current_user.is_authenticated:
            user = load_user(current_user.id)
            return user.isAdmin()
        return current_user.is_authenticated
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

class MyLAnswerView(ModelView):
    column_searchable_list = [User.username, LongQuestions.question, Quizzes.name, User.email]
    form_excluded_columns = ['answer','user','Question']
    def is_accessible(self):
        if current_user.is_authenticated:
            user = load_user(current_user.id)
            return user.isAdmin()
        return current_user.is_authenticated
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

class MyMarksView(ModelView):
    column_searchable_list = [Quizzes.name, User.username, quizMarks.mark, User.email]
    def is_accessible(self):
        if current_user.is_authenticated:
            user = load_user(current_user.id)
            return user.isAdmin()
        return current_user.is_authenticated
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))


class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        if current_user.is_authenticated:
            user = load_user(current_user.id)
            return user.isAdmin() 
        return current_user.is_authenticated
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

admin = Admin(app, index_view=MyAdminIndexView(), name="Quizards")

admin.add_view(MyModelView(User, db.session))
admin.add_view(MyModelView(Post, db.session))
admin.add_view(MyModelView(Quizzes, db.session))
admin.add_view(MyQuestionView(Questions, db.session))
admin.add_view(MyMCQuestionView(multiChoice, db.session))
admin.add_view(MyLQuestionView(LongQuestions, db.session))
admin.add_view(MyLAnswerView(LongAnswers, db.session))
admin.add_view(MyMarksView(quizMarks, db.session))
admin.add_link(MenuLink(name='Back to Website', category='', url='/'))