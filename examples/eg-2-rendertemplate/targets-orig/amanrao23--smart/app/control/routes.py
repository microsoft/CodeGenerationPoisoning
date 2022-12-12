from flask import render_template,request,Blueprint,url_for, redirect
from flask_login import  login_user, current_user

from app.twitter_credentials import CONSUMER_KEY, CONSUMER_SECRET

control=Blueprint('control',__name__)
from app.control.forms import Newctrlcntrform,Loginctrlform,Parametersform
from app import db, login_manager, twitter_credentials
from app.models import Control,Allusers,Alltweets
from functools import wraps
import tweepy
from tweepy import OAuthHandler
import sys
import jsonpickle
import os
import datetime


def login_required(role="admin"):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if ((current_user.role != role) and (role != "admin")):
                return login_manager.unauthorized()
            return fn(*args, **kwargs)

        return decorated_view

    return wrapper

@control.route('/registercontrol', methods=['GET', 'POST'])  # registration of a control centre
def registercontrol():
    form = Newctrlcntrform()
    if form.validate_on_submit():
        newuser = Allusers(username=form.username.data, password=form.password.data, role='admin')
        new_centre = Control(c_name=form.name.data, c_username=form.username.data, c_password=form.password.data)
        db.session.add(new_centre)
        db.session.add(newuser)
        db.session.commit()
        return redirect(url_for('control.logincontrol'))
    return render_template('registercontrol.html', form=form)


@control.route('/logincontrol', methods=['GET', 'POST'])  # login of a control centre
def logincontrol():
    form = Loginctrlform()
    if form.validate_on_submit():
        # return form.username.data + ' ' + form.password.data
        user = Allusers.query.filter_by(username=form.username.data).first()
        controluser = Control.query.filter_by(c_username=form.username.data).first()
        if user and controluser:
            if (user.password == form.password.data):
                login_user(user, remember=form.remember.data)
                return redirect(url_for('control.dashboard'))
        return '<h1>Invalid username or password</h1>'
        # return '<h1>' + form.username.data + ' ' + form.password.data + '</h1>'
    return render_template('login.html', form=form)


@control.route('/dashboard', methods=['GET','POST'])
@login_required(role="admin")
def dashboard():
    form=Parametersform()
    if form.validate_on_submit():
        auth = OAuthHandler(CONSUMER_KEY,CONSUMER_SECRET)
        auth.set_access_token(twitter_credentials.ACCESS_TOKEN, twitter_credentials.ACCESS_TOKEN_SECRET)

        api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

        searchQuery = form.searchQuery.data  # this is what we're searching for
        maxTweets = form.maxTweets.data  # Some arbitrary large number
        tweetsPerQry = form.tweetsPerQry.data  # this is the max the API permits
        geo = "28.704060,77.102493,400km"
        # If results from a specific ID onwards are reqd, set since_id to that ID.
        # else default to no lower limit, go as far back as API allows
        sinceId = None

        places = []
        time = []
        tweets = []

        # If results only below a specific ID are, set max_id to that ID.
        # else default to no upper limit, start from the most recent tweet matching the search query.
        max_id = -1

        tweetCount = 0
        print("Downloading max {0} tweets".format(maxTweets))

        while tweetCount < maxTweets:
            c=0
            try:
                if (max_id <= 0):
                    if (not sinceId):
                        new_tweets = api.search(q=searchQuery, count=tweetsPerQry,geocode=geo, tweet_mode="extended")
                    else:
                        new_tweets = api.search(q=searchQuery, count=tweetsPerQry,
                                                since_id=sinceId,geocode=geo, tweet_mode="extended")
                else:
                    if (not sinceId):
                        new_tweets = api.search(q=searchQuery, count=tweetsPerQry,
                                                max_id=str(max_id - 1),geocode=geo, tweet_mode="extended")
                    else:
                        new_tweets = api.search(q=searchQuery, count=tweetsPerQry,
                                                max_id=str(max_id - 1),
                                                since_id=sinceId,geocode=geo, tweet_mode="extended")
                if not new_tweets:
                    print("No more tweets found")
                    break
                for tweet in new_tweets:
                    # add data to lists

                    # 1. creted at
                    time.append((tweet.created_at.month, tweet.created_at.year))

                    # location of user
                    places.append(tweet.user.location)

                    # text of tweet
                    tweets.append(tweet.full_text)
                    print(tweet.full_text[0])

                    if(tweet.full_text[0]=='R' and tweet.full_text[1]=='T'):
                        c=c+1

                    else:
                        # write in db
                        tweet_id = int(datetime.datetime.now().strftime("%f"))
                        tweet_text = jsonpickle.encode(tweet.full_text, unpicklable=False)
                        entry = Alltweets(id=tweet_id, content=tweet_text,control_id=current_user.id )
                        db.session.add(entry)
                        db.session.commit()
                tweetCount += (len(new_tweets)-c)
                print("Downloaded {0} tweets".format(tweetCount))
                max_id = new_tweets[-1].id

            except tweepy.TweepError as e:
                # Just exit if any error
                print("some error : " + str(e))
                break
        return redirect(url_for('control.dashboard'))
    return render_template('dashboard.html',form=form, name=current_user.username)
