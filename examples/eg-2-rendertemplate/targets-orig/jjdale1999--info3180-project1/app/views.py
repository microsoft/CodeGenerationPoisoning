"""
Flask Documentation:     http://flask.pocoo.org/docs/
Jinja2 Documentation:    http://jinja.pocoo.org/2/documentation/
Werkzeug Documentation:  http://werkzeug.pocoo.org/documentation/
This file creates your application.
"""
import os
from app import app, db
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user, login_required
from app.forms import CreateProfile
from app.models import UserProfile
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
import datetime

def format_date_joined(dat):
    return  dat.strftime("%B %d, %Y") 
###
# Routing for your application.
###

@app.route('/')
def home():
    """Render website's home page."""
    return render_template('home.html')


@app.route('/about/')
def about():
    """Render the website's about page."""
    return render_template('about.html')

@app.route('/profile',methods=['POST', 'GET'])
def profile():
    createprofile = CreateProfile()
    
    if request.method == "POST" and  createprofile.validate_on_submit():
                fname = createprofile.fname.data
                lname = createprofile.lname.data
                email = createprofile.email.data
                location= createprofile.location.data
                gender = createprofile.gender.data
                biography=createprofile.biography.data
                photo= createprofile.photo.data
                created_date=format_date_joined(datetime.datetime.now())
                filename=secure_filename(photo.filename)
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
                user = UserProfile(fname, lname, email, location,gender,biography,'/uploads/'+filename,created_date)
                db.session.add(user)
                db.session.commit()

                return redirect(url_for('profiles'))
    else:
                flash_errors(createprofile)
    return render_template('addprofile.html',form=createprofile)    

@app.route('/profiles')
def profiles():
    user = UserProfile.query.all()
    return render_template('profiles.html',users=user)
    

@app.route('/profile/<userid>')
def profileuser(userid):
    """Render the website's about page."""  
    user = UserProfile.query.get(userid)
    if user is not None:
        fname = user.fname
        lname = user.lname
        email = user.email
        location= user.location
        gender = user.gender
        biography=user.biography
        photo= user.photo
        created_date=user.created_date
        # return render_template('about.html', name="Mary Jane")
        return render_template('profile.html',fname=fname,lname=lname,email=email,location=location,gender=gender,biography=biography,photo=photo,created_date=created_date)
    flash("user not found",'danger')
    return render_template('404.html')
# Flash errors from the form if validation fails
def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).label.text,
                error
            ), 'danger')

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


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port="8080")
