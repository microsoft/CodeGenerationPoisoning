from flask import Flask, render_template, request, url_for, redirect, abort
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_mail import Mail, Message
from datetime import datetime
import os
import uuid

from src.common.database import Database
from src.models.trailer import Trailer
from src.models.event import Event

from src.models.user import User

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'its-secret-but-not-too-secret'
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = 1
app.config['MAIL_USERNAME'] = 'compscicorner@gmail.com'
app.config['MAIL_PASSWORD'] = 'NCF2020S@rasota'

login = LoginManager(app)
login.login_view = 'admin_login'

mail = Mail(app)


@app.before_first_request
def initialize_database():
    """Initializes MongoDB Database before application starts running"""
    Database.initialize()

uploads_dir = os.path.join(app.root_path, 'static', 'submissions', 'trailers')


@app.route('/')
def home():
    """Renders the submission choice page"""
    if Database.is_empty(collection='admin_users'):
        User.add_admin()
    return choose_submission()


@app.route('/submit')
def choose_submission():
    """Renders the submission page, where users can choose between either submitting a project or a trailer."""
    return render_template("submit.html", title="Comp Sci Corner | Make a Submission")


@app.route('/display')
def display_page():
    """Renders the main display that will be shown in the HNS 160's Hallway."""
    Event.remove_expired()
    Trailer.remove_expired()

    events = Event.get_approved()
    trailers = Trailer.get_queued()
    script = os.path.join('js', 'display.js')

    return render_template("display.html", title="Comp Sci Corner | Display", events=events, n_events=len(events),
                           trailers=trailers, n_trailers=len(trailers), script=script)


@app.route('/submit/trailer/handle-submission', methods=['POST'])
def handle_trailer_submission():
    """Called after submit_trailer(), will take information user submitted and create a Trailer-object to be stored in MongoDB"""
    _id = uuid.uuid4().hex
    author = request.form.get('name')
    email = request.form.get('email')
    display_email = request.form.get('display-email')
    title = request.form.get('title')

    trailer = request.files.get('trailer')
    trailer_path = os.path.join(uploads_dir, str(_id) + ".mp4")
    trailer.save(trailer_path)

    link = request.form.get('link')

    new_post = Trailer(author, email, display_email, title, trailer_path, datetime.now(), link, _id)
    new_post.save_to_mongo()

    return redirect(url_for('confirm_submission'))


@app.route('/submit/event/handle-submission', methods=['POST'])
def handle_event_submission():
    """Called after submit_event(), will take information user submitted and create an Event-object to be stored in MongoDB"""
    author = request.form.get('name')
    email = request.form.get('email')
    title = request.form.get('title')
    date = request.form.get('date')
    time = request.form.get('time')
    location = request.form.get('location')
    description = request.form.get('description')

    new_post = Event(author, email, title, date, time, location, description)
    new_post.save_to_mongo()

    return redirect(url_for('confirm_submission'))


@app.route('/submit/confirm')
def confirm_submission():
    """After user submits an event or trailer, they are redirected here and prompted to make another submission."""
    return render_template("confirm-submission.html", title="Comp Sci Corner | Submission Confirmation")


@app.route('/submit/project')
def submit_project():
    """Renders submission form for Trailers"""
    return render_template("submit-project.html", title="Comp Sci Corner | Submit a Project")


@app.route('/submit/event')
def submit_event():
    """Renders submission form for Events"""
    return render_template("submit-event.html", title="Comp Sci Corner | Submit an Event")


@app.route('/admin')
def admin():
    """Returns function to render the admin login-page."""
    return admin_login()


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Renders login-page for admin account. Admins are able to access event/trailer submissions to approve them for display."""
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    if request.method == 'POST':
        password = request.form.get('pwd')
        user = User.get_user("Admin")
        if user is None or not user.check_password(password):
            return render_template("login.html", invalid=True)
        login_user(user)
        return redirect(request.args.get('next') or url_for('home'))
    return render_template("login.html", title="Comp Sci Corner | Admin Login", invalid=False)


@app.route('/logout')
@login_required
def logout():
    """Redirects user to home and logs them out"""
    logout_user()
    return redirect(url_for('home'))


@app.route('/admin/review/projects')
@login_required
def review_trailers_home():
    """Renders the homepage for admins reviewing trailers."""
    return render_template("review-trailers-home.html", title="Comp Sci Corner | Project Review")


@app.route('/admin/review/projects/<i>')
@login_required
def review_trailers(i):
    """Renders the review page for trailers, User must be logged in as admin to access. The user can approve or deny pending
    submissions. Approved trailers join the queue to be put on the board, denied ones should send an email back to the user
    who submitted it with revisions they must apply."""
    trailers = Trailer.get_pending()

    if len(trailers) == 0:
        return redirect(url_for('review_trailers_home'))

    first = 0
    last = len(trailers)-1
    i = max(first, min(last, int(i)))
    current = trailers[i]

    return render_template("review-trailers.html", title="Comp Sci Corner | Project Review", n=len(trailers),
                           current=current, i=i, first=first, last=last)


@app.route('/admin/approve/trailer/<trailer_id>')
def approve_trailer(trailer_id, index=0):
    """Approves a trailer from the trailer page. Sends an email to the trailer owner."""
    trailer = Trailer.from_mongo(trailer_id)
    send_email(subject="Your Comp Sci Corner submission was approved!",
               recipient=trailer.email,
               text_body=render_template("trailer_approve_email.txt", trailer=trailer),
               html_body=render_template("trailer_approve_email.html", trailer=trailer))
    Trailer.approve(trailer_id)
    return redirect(url_for('review_trailers', i=index))


@app.route('/admin/deny/trailer/<trailer_id>', methods=['GET', 'POST'])
def deny_trailer(trailer_id, index=0):
    """Denies a trailer from the trailer page. Sends an email to the trailer owner."""
    trailer = Trailer.from_mongo(trailer_id)
    comments = request.form.get('comments')
    print(comments)
    send_email(subject="Your Comp Sci Corner submission was denied.",
               recipient=trailer.email,
               text_body=render_template("trailer_deny_email.txt", trailer=trailer, comments=comments),
               html_body=render_template("trailer_deny_email.html", trailer=trailer, comments=comments))
    Trailer.deny(trailer_id)
    return redirect(url_for('review_trailers', i=index))


# Event Review():
@app.route('/admin/review/events')
@login_required
def review_events():
    """Renders Event review page, User must be logged in as an admin to access."""
    events = Event.get_pending()
    return render_template("review-events.html", title="Comp Sci Corner | Review Events", events=events, n=len(events))


@app.route('/admin/approve/event/<event_id>')
def approve_event(event_id):
    """Approves an event and adds it to the active rotation. Sends an email to the event owner."""
    event = Event.from_mongo(event_id)
    send_email(subject="Your Comp Sci Corner event was approved!",
               recipient=event.email,
               text_body=render_template("event_approve_email.txt", event=event),
               html_body=render_template("event_approve_email.html", event=event))
    Event.approve(event_id)
    return redirect(url_for('review_events'))


@app.route('/admin/deny/event/<event_id>')
def deny_event(event_id):
    """Rejects an event and removes it. Sends an email to the event owner."""
    event = Event.from_mongo(event_id)
    send_email(subject="Your Comp Sci Corner event was denied.",
               recipient=event.email,
               text_body=render_template("event_deny_email.txt", event=event),
               html_body=render_template("event_deny_email.html", event=event))
    Event.deny(event_id)
    return redirect(url_for('review_events'))


@login.user_loader
def load_user(id):
    """loads a current user based on id

    :param: (str) id, corresponds to the id of a user in the database
    """
    return User.get_user_by_id(id)

def send_email(subject, recipient, text_body, html_body):
    """Sends an email from compscicorner@gmail.com.

    :param: (str) subject, the subject of the email
    :param: (str) recipient, the email address of the recipient
    :param: (str) text_body, the plain text body of the email
    :param: (str) html_body, the html template for the email
    """
    msg = Message(subject, sender="compscicorner@gmail.com", recipients=[recipient])
    msg.body = text_body
    msg.html = html_body
    mail.send(msg)
