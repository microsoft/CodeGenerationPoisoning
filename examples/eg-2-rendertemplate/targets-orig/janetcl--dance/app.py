#!/usr/bin/env python

#-----------------------------------------------------------------------
# app.py
# Author: Janet Lee
# Based on penny.py by Bob Dondero
#-----------------------------------------------------------------------

import os
import requests_oauthlib
from requests_oauthlib.compliance_fixes import facebook_compliance_fix

from sys import argv
from flask import Flask, request, make_response, redirect, url_for
from flask import render_template, jsonify
from flask_heroku import Heroku
from dataclasses import dataclass

# From https://realpython.com/flask-google-login/
import sqlite3
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
    UserMixin,
)
from oauthlib.oauth2 import WebApplicationClient
import requests
import json

import cloudinary
import cloudinary.uploader
import cloudinary.api
import cloudinary.utils
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

cloudinary.config(
  cloud_name = "hdcz0vo9p",
  api_key = "154722578765685",
  api_secret = "mgwaIcY8F5NRyiI8QXOeDTD33dc"
)

# Flask app setup
app = Flask(__name__, template_folder='.')
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

# Toggle between these two to switch between local testing and Heroku
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost/dance'
# heroku = Heroku(app)

db = SQLAlchemy(app)

# Create our database model
@dataclass
class User(db.Model, UserMixin):
    __tablename__ = "users"
    id: str
    name: str
    email: str
    profile_pic: str

    id = db.Column(db.String(120), primary_key=True, unique=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    profile_pic = db.Column(db.String(), unique=True)

    def __init__(self, id, name, email, profile_pic):
        self.id = id
        self.name = name
        self.email = email
        self.profile_pic = profile_pic

    def __repr__(self):
        return '<E-mail %r>' % self.email

# Create our dance database model
@dataclass
class Dance(db.Model):
    __tablename__ = "dances"
    id: int
    user_id: str
    user_email: str
    dance_name: str
    dancers: 'typing.Any'
    keyframes: 'typing.Any'
    number_of_keyframes: int
    image: str
    audioFileName: str
    audioURL: str

    id = db.Column(db.Integer(), primary_key=True, unique=True)
    user_id = db.Column(db.String(120), primary_key=True)
    user_email = db.Column(db.String(120))
    dance_name = db.Column(db.String(120))
    dancers = db.Column(db.String())
    keyframes = db.Column(db.String())
    number_of_keyframes = db.Column(db.Integer)
    image = db.Column(db.String())
    audioFileName = db.Column(db.String())
    audioURL = db.Column(db.String())

    def __init__(self, id, user_id, user_email, dance_name, dancers, keyframes, number_of_keyframes, image, audioFileName, audioURL):
        self.id = id
        self.user_id = user_id
        self.user_email = user_email
        self.dance_name = dance_name
        self.dancers = dancers
        self.keyframes = keyframes
        self.number_of_keyframes = number_of_keyframes
        self.image = image
        self.audioFileName = audioFileName
        self.audioURL = audioURL

    def __repr__(self):
        return '<Dancers %r>' % self.dancers

# Facebook Login
FB_CLIENT_ID = os.environ.get("FB_CLIENT_ID")
FB_CLIENT_SECRET = os.environ.get("FB_CLIENT_SECRET")

FB_AUTHORIZATION_BASE_URL = "https://www.facebook.com/dialog/oauth"
FB_TOKEN_URL = "https://graph.facebook.com/oauth/access_token"

FB_SCOPE = ["email"]

# Google Login
GOOGLE_CLIENT_ID = "966768610728-t9b4b1t6gbth733k5el104tgt85edfb1.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "ndTjBKN3gSvsxW_zGxgD8Mfw"

GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

# This allows us to use a plain HTTP callback
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

#-----------------------------------------------------------------------

# User session management setup
# https://flask-login.readthedocs.io/en/latest
login_manager = LoginManager()
login_manager.init_app(app)

# OAuth 2 client setup
client = WebApplicationClient(GOOGLE_CLIENT_ID)

# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(user_id)

#-----------------------------------------------------------------------

@app.route("/")
def index():
    if current_user.is_authenticated:
        dances = db.session.query(Dance).filter(Dance.user_id == current_user.id).all()

        # Send user to dance page
        return render_template('dance.html',
            name=current_user.name,
            email=current_user.email,
            avatar_url=current_user.profile_pic,
            dances=dances)

    else:
        return render_template('index.html')

# Toggle between these two to switch between local testing and Heroku
# Your ngrok url, obtained after running "ngrok http 8000"
# URL = "https://2d1855e0.ngrok.io"
URL = "https://dancetigers.herokuapp.com"

@app.route("/fb-login")
def fbLogin():
    facebook = requests_oauthlib.OAuth2Session(
        FB_CLIENT_ID, redirect_uri=URL + "/fb-callback", scope=FB_SCOPE
    )
    authorization_url, _ = facebook.authorization_url(FB_AUTHORIZATION_BASE_URL)

    return redirect(authorization_url)


@app.route("/fb-callback")
def fbCallback():
    facebook = requests_oauthlib.OAuth2Session(
        FB_CLIENT_ID, scope=FB_SCOPE, redirect_uri=URL + "/fb-callback"
    )

    # we need to apply a fix for Facebook here
    facebook = facebook_compliance_fix(facebook)

    facebook.fetch_token(
        FB_TOKEN_URL,
        client_secret=FB_CLIENT_SECRET,
        authorization_response=request.url,
    )

    # Fetch a protected resource, i.e. user profile, via Graph API

    facebook_user_data = facebook.get(
        "https://graph.facebook.com/me?fields=id,name,email,picture{url}"
    ).json()

    unique_id = facebook_user_data["id"]
    email = facebook_user_data["email"]
    name = facebook_user_data["name"]
    picture_url = facebook_user_data.get("picture", {}).get("data", {}).get("url")

    # Create a user in your db with the information provided
    # by Facebook
    id = unique_id
    profile_pic = picture_url

    user = User(id, name, email, profile_pic)

    # Doesn't exist? Add it to the database.
    if not db.session.query(User).filter(User.id == id).count():
        db.session.add(user)
        db.session.commit()

    # Begin user session by logging the user in
    login_user(user)

    # Send user to dance page
    if current_user.is_authenticated:
        return redirect("/")
    # else:
    dances = db.session.query(Dance).filter(Dance.user_id == id).all()

    # Send user to dance page
    return render_template('dance.html',
        name=name,
        email=email,
        avatar_url=profile_pic,
        dances=dances)

def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()

@app.route("/google-login")
def googleLogin():

    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for Google login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "-callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)


@app.route("/google-login-callback")
def googleCallback():
    # Get authorization code Google sent back to you
    code = request.args.get("code")

    # Find out what URL to hit to get tokens that allow you to ask for
    # things on behalf of a user
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    # Prepare and send a request to get tokens! Yay tokens!
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json()))

    # Now that you have tokens (yay) let's find and hit the URL
    # from Google that gives you the user's profile information,
    # including their Google profile image and email
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    # You want to make sure their email is verified.
    # The user authenticated with Google, authorized your
    # app, and now you've verified their email through Google!
    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
    else:
        return "User email not available or not verified by Google.", 400

    # Create a user in your db with the information provided
    # by Google
    id = unique_id
    name = users_name
    email = users_email
    profile_pic = picture

    user = User(id, name, email, profile_pic)

    # Doesn't exist? Add it to the database.
    if not db.session.query(User).filter(User.id == id).count():
        db.session.add(user)
        db.session.commit()

    # Begin user session by logging the user in
    login_user(user)

    # Send user to dance page
    if current_user.is_authenticated:
        return redirect("/")
    # else:
    # dances = db.session.query(Dance).filter(Dance.user_id == id).all()

    # Send user to dance page
    return render_template('dance.html',
        name=name,
        email=email,
        avatar_url=profile_pic)

@app.route("/saveDance", methods = ["POST"])
@login_required
def save_dance():

    id = request.json['dance_id']
    user_id = current_user.id
    user_email = current_user.email
    dance_name = request.json['dance_name']
    dancers = request.json['dancers']
    keyframes = request.json['keyframes']
    number_of_keyframes = request.json['number_of_keyframes']
    imageStream = request.json['image']
    audioFileName = request.json['audioFileName']
    audioURL = request.json['audioURL']

    response = cloudinary.uploader.upload(imageStream)
    imageURL, options = cloudinary.utils.cloudinary_url(response['public_id'])

    # # Doesn't exist? Add it to the database.
    if id < 0 or not db.session.query(Dance).filter(Dance.id == id).count():
        # id = db.session.query(Dance).count()
        if db.session.query(Dance).count() == 0:
            max_id = -1
        else:
            max_id = db.session.query(func.max(Dance.id)).scalar()
        id = max_id + 1
        dance = Dance(id, user_id, user_email, dance_name, dancers, keyframes, number_of_keyframes, imageURL, audioFileName, audioURL)
        db.session.add(dance)
        db.session.commit()
    else:
        # # If in the database, update the dance with the new values.
        dance = db.session.query(Dance).filter(Dance.id == id).first()
        dance.dance_name = dance_name
        dance.dancers = dancers
        dance.keyframes = keyframes
        dance.number_of_keyframes = number_of_keyframes
        dance.image = imageURL
        dance.audioFileName = audioFileName
        dance.audioURL = audioURL
        db.session.commit()

    return jsonify({"Success": "Nicely done", "id": id})

@app.route("/saveAudio", methods = ["POST"])
@login_required
def save_audio():

    audio = request.files['audio']
    response = cloudinary.uploader.upload(audio, resource_type = "video")
    audioURL, options = cloudinary.utils.cloudinary_url(response['public_id'], resource_type="video")
    db.session.commit()
    return jsonify({"Success": "Nicely done", "audioURL": audioURL})

@app.route("/getDances", methods = ["GET"])
@login_required
def get_dances():
    next_available_id = db.session.query(Dance).count()
    # Practice getting the dances for the given user
    dances = db.session.query(Dance).filter(Dance.user_id == current_user.id).order_by(Dance.id).all()
    jsonify(dances)
    if db.session.query(Dance).filter(Dance.user_id == current_user.id).count():
        return jsonify({"dances": dances, "next_available_id": next_available_id})
    else:
        print("No dances")
        return jsonify({"dances": dances, "next_available_id": next_available_id})

@app.route("/deleteDance", methods = ["POST"])
@login_required
def delete_dance():
    id = request.json['dance_id']
    # Practice getting the dances for the given user
    dance = db.session.query(Dance).filter(Dance.id == id).first()
    if dance:
        db.session.delete(dance)
        db.session.commit()
        print("Deleted dance: ", dance)
        return jsonify({"Success": "Nicely done"})
    else:
        print("No matching dance found")
        return jsonify({"Success": "Nicely done"})

@app.route("/logout")

def logout():
    logout_user()
    return redirect(url_for("index"))

#-----------------------------------------------------------------------

if __name__ == '__main__':
    if len(argv) != 2:
        print('Usage: ' + argv[0] + ' port')
        exit(1)
    app.run(host='127.0.0.1', port=int(argv[1]), debug=True)
