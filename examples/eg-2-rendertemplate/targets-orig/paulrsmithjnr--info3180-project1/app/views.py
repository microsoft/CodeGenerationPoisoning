"""
Flask Documentation:     http://flask.pocoo.org/docs/
Jinja2 Documentation:    http://jinja.pocoo.org/2/documentation/
Werkzeug Documentation:  http://werkzeug.pocoo.org/documentation/
This file creates your application.
"""
import os
import psycopg2 
from app import app, db
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user, login_required
from app.forms import ProfileForm
from app.models import Profile
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash

###
# Routing for your application.
###

def connect_db():
 return psycopg2.connect(host="ec2-23-22-156-110.compute-1.amazonaws.com", database="datdia6j8gufho", user="jrwagwsvveqdyq", password="d3b01edc599b779de8e660424263867202089a8783719506324e993913c68e69")

@app.route('/')
def home():
    """Render website's home page."""
    return render_template('home.html')


@app.route('/about/')
def about():
    """Render the website's about page."""
    return render_template('about.html')

@app.route('/profile', methods = ['GET', 'POST'])
def profile():
    """Render the website's profile page."""
    profilePage = ProfileForm()

    if request.method == 'POST':
        if profilePage.validate_on_submit():

            firstName = profilePage.firstName.data
            lastName = profilePage.lastName.data
            gender = profilePage.gender.data
            email = profilePage.email.data
            location = profilePage.location.data
            biography = profilePage.biography.data
            photo = profilePage.photo.data

            filename = secure_filename(photo.filename)
            photo.save(os.path.join(
                app.config['UPLOAD_FOLDER'], filename
            ))

            profile = Profile(first_name=firstName, last_name=lastName, gender=gender, email=email, location=location, biography=biography, profile_picture="uploads/"+filename)
            db.session.add(profile)
            db.session.commit()

            flash('New Profile Created!', 'success')
            return redirect(url_for('profiles'))
        else:
            flash_errors(profilePage)

    return render_template('profile.html', form = profilePage)

@app.route('/profiles')
def profiles():
    """Render the website's profiles page."""
    db = connect_db()
    cur = db.cursor()
    cur.execute('SELECT * FROM userProfiles')
    profiles = cur.fetchall()
    return render_template('profiles.html', profiles=profiles)

@app.route('/profile/<userid>')
def loadprofile(userid):
    """Render the website's profiles page."""
    profile = Profile.query.filter_by(id=int(userid)).first()
    return render_template('loadprofile.html', profile=profile)


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
    and also to cache the rendered page for 10 minutes.
    """
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response


@app.errorhandler(404)
def page_not_found(error):
    """Custom 404 page."""
    return render_template('404.html'), 404

def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).label.text,
                error
), 'danger')

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port="8080")
