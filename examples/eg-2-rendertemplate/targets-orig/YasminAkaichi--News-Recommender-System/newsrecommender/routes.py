import secrets
import requests
from elasticsearch import Elasticsearch,helpers
import pandas as pd
import numpy as np
from flask_table import Table, Col
from csv import DictReader
from flask import Flask,render_template, url_for, flash, redirect, request
from flask_login import login_user, current_user, logout_user, login_required,LoginManager,UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from sqlalchemy.orm.exc import NoResultFound
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.externals import joblib
from sklearn.neighbors import KNeighborsClassifier
import pickle as pk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
from nltk.stem.snowball import SnowballStemmer
from datetime import datetime
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_dance.contrib.twitter import make_twitter_blueprint
from flask_dance.consumer import oauth_authorized, oauth_error
from flask_dance.consumer.storage.sqla import SQLAlchemyStorage
import warnings
warnings.filterwarnings("ignore")
import sqlite3
import nltk
import string
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.metrics import confusion_matrix
from sklearn import metrics
from sklearn.metrics import roc_curve, auc
from nltk.stem.porter import PorterStemmer
import string
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.stem.wordnet import WordNetLemmatizer
from gensim.models import Word2Vec
from gensim.models import KeyedVectors
from tqdm import tqdm
import os
import plotly.graph_objs as go
from chart_studio.plotly import plotly
import plotly.offline as offline
offline.init_notebook_mode()
from collections import Counter
import csv
import datetime as dt
from twitterscraper import query_tweets
from twitterscraper import query_tweets_from_user as qtfu
from twitterscraper.query import query_user_info
from multiprocessing import Pool
import time
from IPython.display import display
from bs4 import BeautifulSoup
# generate random integer values
from random import seed
from random import randint

def preprocess_text(text_data):
    preprocessed_text = []
    # tqdm is for printing the status bar
    for sentance in tqdm(text_data):
        sent = decontracted(sentance)
        sent = sent.replace('\\r', ' ')
        sent = sent.replace('\\n', ' ')
        sent = sent.replace('\\"', ' ')
        sent = re.sub('[^A-Za-z0-9]+', ' ', sent)
        # https://gist.github.com/sebleier/554280
        sent = ' '.join(e for e in sent.split() if e.lower() not in stopwords)
        preprocessed_text.append(sent.lower().strip())
    return preprocessed_text
def decontracted(phrase):
    # specific
    phrase = re.sub(r"won't", "will not", phrase)
    phrase = re.sub(r"can\'t", "can not", phrase)

    # general
    phrase = re.sub(r"n\'t", " not", phrase)
    phrase = re.sub(r"\'re", " are", phrase)
    phrase = re.sub(r"\'s", " is", phrase)
    phrase = re.sub(r"é", "e", phrase)
    phrase = re.sub(r"ç", "c", phrase)
    phrase = re.sub(r"ï", "i", phrase)
    phrase = re.sub(r"\'d", " would", phrase)
    phrase = re.sub(r"\'ll", " will", phrase)
    phrase = re.sub(r"\'t", " not", phrase)
    phrase = re.sub(r"\'ve", " have", phrase)
    phrase = re.sub(r"\'m", " am", phrase)
    return phrase
stopwords= ['i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've",\
            "you'll", "you'd", 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', \
            'she', "she's", 'her', 'hers', 'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their',\
            'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', "that'll", 'these', 'those', \
            'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', \
            'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', \
            'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after',\
            'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further',\
            'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more',\
            'most', 'other', 'some', 'such', 'only', 'own', 'same', 'so', 'than', 'too', 'very', \
            's', 't', 'can', 'will', 'just', 'don', "don't", 'should', "should've", 'now', 'd', 'll', 'm', 'o', 're', \
            've', 'y', 'ain', 'aren', "aren't", 'couldn', "couldn't", 'didn', "didn't", 'doesn', "doesn't", 'hadn',\
            "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't", 'ma', 'mightn', "mightn't", 'mustn',\
            "mustn't", 'needn', "needn't", 'shan', "shan't", 'shouldn', "shouldn't", 'wasn', "wasn't", 'weren', "weren't", \
            'won', "won't", 'wouldn', "wouldn't"]

class RegistrationForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')


class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


    


class UpdateAccountForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Update')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is taken. Please choose a different one.')

class CommentForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Comment')


app = Flask(__name__)
app.config['SECRET_KEY'] = 'aa7fbd472d40082d93ef896fc5934cd9'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['TWITTER_OAUTH_CLIENT_KEY']='Cru31GFfxRfOFso0R07I5pZx3'
app.config['TWITTER_OAUTH_CLIENT_SECRET']='kmicg6cVrlBigO2OtkfAi58HMO2NL635L58OUmLieIV35KR8bj'
SQLALCHEMY_TRACK_MODIFICATIONS = False
db = SQLAlchemy(app)
db.init_app(app)
bcrypt = Bcrypt(app)

login_manager1 = LoginManager()
login_manager1.login_view = 'twitter.login'
login_manager1.init_app(app)



@login_manager1.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

db.init_app(app)
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    image_file = db.Column(db.String(20), nullable=True, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    comments = db.relationship('Comment', backref='author', lazy=True)
    recommendation=db.relationship('Recommendation', backref='author', lazy=True)
    article = db.relationship('Profile', backref='author', lazy=True)
    def __repr__(self):
        return f"User('{self.username}','{self.email}', '{self.image_file}')"

class OAuth(OAuthConsumerMixin, db.Model):
    provider_user_id = db.Column(db.String(256), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    user1 = db.relationship(User)

blueprint = make_twitter_blueprint(
    storage=SQLAlchemyStorage(OAuth, db.session, user=current_user)
)
app.register_blueprint(blueprint, url_prefix="/login")



# setup login manager




@oauth_authorized.connect_via(blueprint)
def twitter_logged_in(blueprint, token):
    if not token:
        flash("Failed to log in.", category="error")
        return False

    resp = blueprint.session.get("account/verify_credentials.json")
    if not resp.ok:
        msg = "Failed to fetch user info."
        flash(msg, category="error")
        return False

    info = resp.json()
    user_id = info["id_str"]
    current_user.username=info["screen_name"]

    # Find this OAuth token in the database, or create it
    query = OAuth.query.filter_by(
        provider=blueprint.name,
        provider_user_id=user_id,
    )
    try:
        oauth = query.one()
    except NoResultFound:
        oauth = OAuth(
            provider=blueprint.name,
            provider_user_id=user_id,
            token=token,
        )
    user = User.query.filter_by(username=info["screen_name"]).first()

    if oauth.user1 and user:
        login_user(oauth.user1)
        flash("Successfully signed in.")
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('tweet'))

    else:
        # Create a new local user account for this user
        
        user1 = User(username=info["screen_name"],password="True")
        # Associate the new local user account with the OAuth token
        oauth.user1 = user1
        # Save and commit our database models
        db.session.add_all([user1, oauth])
        db.session.commit()
        # Log in the new local user account
        login_user(user1)
        user=info["screen_name"]
        user_info = query_user_info(user)
        limit=10
        lang='english'
        tweets = qtfu(user,limit=limit)
        df=pd.DataFrame(t.__dict__ for t in tweets )
        df = df.drop(['timestamp', 'timestamp_epochs', 'text_html', 'links','img_urls','tweet_url','video_url','is_replied','is_reply_to','parent_tweet_id','reply_to_users','hashtags','has_media'], axis = 1) 
        tweets = df['text'].tolist()
        ptweets = preprocess_text(df['text'].values)
        df['ptweets']= ptweets
        df.to_csv (r'user'+user+'.csv', index = False, header=True)
        user2=user.lower()
        with open('user'+user+'.csv') as f:
            reader= csv.DictReader(f)                             
            helpers.bulk(es, reader, index=user2 , doc_type='tweets')
        os.remove('user'+user+'.csv')
        flash("Successfully signed in.")
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('tweet'))

    # Disable Flask-Dance's default behavior for saving the OAuth token
    return False


# notify on OAuth provider error
@oauth_error.connect_via(blueprint)
def twitter_error(blueprint, message, response):
    msg = (
        "OAuth error from {name}! "
        "message={message} response={response}"
    ).format(
        name=blueprint.name,
        message=message,
        response=response,
    )
    flash(msg, category="error")


login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic=db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"Comment('{self.user_id}','{self.topic}', '{self.date_posted}','{self.content}')"

class Recommendation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title=db.Column(db.String(120),nullable=True)
    content = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Recommendation('{self.user_id}','{self.title}','{self.date}','{self.content}')"

class Profile(db.Model):
    id = db.Column(db.String, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
        nullable=False)
    def __repr__(self):
        return f"Profile('{self.id}','{self.user_id}')"
class Latest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title=db.Column(db.String(120),nullable=True)
    content = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(120), nullable=False)
    topic=db.Column(db.String(120),nullable=False)
    def __repr__(self):
        return f"Latest('{self.id}','{self.title}',,'{self.content}',,'{self.date}','{self.topic}')"


news = pd.read_csv('data.csv')
news_articles = pd.read_csv('ProcessedEnglish_news.csv')

stemmer = SnowballStemmer("english")

nltk.download('punkt')

NUM_RECOMMENDED_ARTICLES=6


def clean_tokenize(document):
    document = re.sub('[^\w_\s-]', ' ',document)       #remove punctuation marks and other symbols
    tokens = nltk.word_tokenize(document)              #Tokenize sentences
    cleaned_article = ' '.join([stemmer.stem(item) for item in tokens])    #Stemming each token
    return cleaned_article

#news = pd.read_csv('flaskblog/EnglishDS.csv')
#news_articles = pd.read_csv('flaskblog/ProcessedEnglish_news.csv')
def getLastNews(newssite_link):

    page = requests.get(newssite_link)
    soup = BeautifulSoup(page.content, 'html.parser')
    for ul in soup.find_all('ul',class_='c-posts c-posts--tile c-posts--grid c-posts--gridMosaic c-posts--highlightFirst l-section__posts'):
        for d in ul.find_all('div',class_='c-posts__inner'):
            for a in d.find_all('a',class_='c-posts__details',href=True,title=True):
                get_link = a['href']
    return get_link
def getLastNewsTitle(newssite_link):
    page = requests.get(newssite_link)
    soup = BeautifulSoup(page.content, 'html.parser')
    for ul in soup.find_all('ul',class_='c-posts c-posts--tile c-posts--grid c-posts--gridMosaic c-posts--highlightFirst l-section__posts'):
        for d in ul.find_all('div',class_='c-posts__inner'):
            for a in d.find_all('a',class_='c-posts__details',title=True):
                title=a['title']
    return title
def getLastNewsDate(newssite_link):

    page = requests.get(newssite_link)
    soup = BeautifulSoup(page.content, 'html.parser')
    for ul in soup.find_all('ul',class_='c-posts c-posts--tile c-posts--grid c-posts--gridMosaic c-posts--highlightFirst l-section__posts'):
        for d in ul.find_all('div',class_='c-posts__inner'):
            for a in d.find_all('a',class_='c-posts__details',href=True,title=True):
                time=a.find('div',class_='c-posts__info').text
    return time
def getLastNewsTopic(newssite_link):
    page = requests.get(newssite_link)
    soup = BeautifulSoup(page.content, 'html.parser')
    for ul in soup.find_all('ul',class_='c-posts c-posts--tile c-posts--grid c-posts--gridMosaic c-posts--highlightFirst l-section__posts'):
        for d in ul.find_all('div',class_='c-posts__inner'):
            for a in d.find_all('a',class_='c-posts__details',href=True,title=True):
                topic=a.find('div',class_='c-posts__info c-posts__info--right c-posts__info--highlight').text
                if (topic=='Canada' or topic=='Crime' or topic=='Money'):
                    topic='World'
                if (topic=='Trending' or topic=='Lifestyle'):
                    topic='Media'   
                if (topic==''):
                    topic=a.find('div',class_='c-posts__info c-posts__info--right c-posts__info--highlight').text
    return topic
def getLastNewsContent(newssite_link):
    page = requests.get(newssite_link)
    soup = BeautifulSoup(page.content, 'html.parser')
    content=soup.find('article',class_='l-article__text js-story-text').p.text

    
    return content

es=Elasticsearch()

@app.route("/Build")
def build ():
    return render_template('build.html')
@app.route("/tweet")
def tweet ():
    return render_template('tweet.html')
@app.route("/predict")
def predict ():
    return render_template('prediction.html')


@app.route("/Society")
def society():
    image=[]
    top=[]
    tit=[]
    date=[]
    res = es.search(index="society", body={"query": {"match_all": {}}})
    for hit in res['hits']['hits']:
        img="%(src)s"% hit["_source"]
        i="%(Title)s"% hit["_source"]
        t="%(Date)s"% hit["_source"]
        d="%(Content)s"% hit["_source"]
        image.append(img)
        tit.append(i)
        top.append(t)
        date.append(d)
        list=zip(image,top,date,tit)


    return render_template('societe.html', society=list)
@app.route("/Sports")
def sports():
    image=[]
    top=[]
    tit=[]
    date=[]
    res = es.search(index="sports", body={"query": {"match_all": {}}})
    for hit in res['hits']['hits']:
        img="%(src)s"% hit["_source"]
        i="%(Title)s"% hit["_source"]
        t="%(Date)s"% hit["_source"]
        d="%(Content)s"% hit["_source"]
        image.append(img)
        tit.append(i)
        top.append(t)
        date.append(d)
        list=zip(image,top,date,tit)


    return render_template('sport.html', sport=list)
@app.route("/art")
def art():
    image=[]
    top=[]
    tit=[]
    date=[]
    res = es.search(index="art", body={"query": {"match_all": {}}})
    for hit in res['hits']['hits']:
        img="%(src)s"% hit["_source"]
        i="%(Title)s"% hit["_source"]
        t="%(Date)s"% hit["_source"]
        d="%(Content)s"% hit["_source"]
        image.append(img)
        tit.append(i)
        top.append(t)
        date.append(d)
        list=zip(image,top,date,tit)


    return render_template('art.html', art=list)
@app.route("/style")
def style():
    image=[]
    top=[]
    tit=[]
    date=[]
    res = es.search(index="style", body={"query": {"match_all": {}}})
    for hit in res['hits']['hits']:
        img="%(src)s"% hit["_source"]
        i="%(Title)s"% hit["_source"]
        t="%(Date)s"% hit["_source"]
        d="%(Content)s"% hit["_source"]
        image.append(img)
        tit.append(i)
        top.append(t)
        date.append(d)
        list=zip(image,top,date,tit)


    return render_template('style.html', art=list)
@app.route("/entertainment")
def entertainment():
    image=[]
    top=[]
    tit=[]
    date=[]
    res = es.search(index="entertainment", body={"query": {"match_all": {}}})
    for hit in res['hits']['hits']:
        img="%(src)s"% hit["_source"]
        i="%(Title)s"% hit["_source"]
        t="%(Date)s"% hit["_source"]
        d="%(Content)s"% hit["_source"]
        image.append(img)
        tit.append(i)
        top.append(t)
        date.append(d)
        list=zip(image,top,date,tit)


    return render_template('entertainment.html', entertainment=list)
@app.route("/world")
def world():
    image=[]
    top=[]
    tit=[]
    date=[]
    res = es.search(index="world", body={"query": {"match_all": {}}})
    for hit in res['hits']['hits']:
        img="%(src)s"% hit["_source"]
        i="%(Title)s"% hit["_source"]
        t="%(Date)s"% hit["_source"]
        d="%(Content)s"% hit["_source"]
        image.append(img)
        tit.append(i)
        top.append(t)
        date.append(d)
        list=zip(image,top,date,tit)


    return render_template('world.html', world=list)


@app.route("/sci_tech")
def sci_tech():
    image=[]
    top=[]
    tit=[]
    date=[]
    res = es.search(index="sci_tech", body={"query": {"match_all": {}}})
    for hit in res['hits']['hits']:
        img="%(src)s"% hit["_source"]
        i="%(Title)s"% hit["_source"]
        t="%(Date)s"% hit["_source"]
        d="%(Content)s"% hit["_source"]
        image.append(img)
        tit.append(i)
        top.append(t)
        date.append(d)
        list=zip(image,top,date,tit)


    return render_template('tech.html', tech=list)
@app.route("/Politics")
def politics():
    image=[]
    top=[]
    tit=[]
    date=[]
    res = es.search(index="politics", body={"query": {"match_all": {}}})
    for hit in res['hits']['hits']:
        img="%(src)s"% hit["_source"]
        i="%(Title)s"% hit["_source"]
        t="%(Date)s"% hit["_source"]
        d="%(Content)s"% hit["_source"]
        image.append(img)
        tit.append(i)
        top.append(t)
        date.append(d)
        list=zip(image,top,date,tit)


    return render_template('politique.html', politique=list)
@app.route("/Economy")
def economy():
    image=[]
    top=[]
    tit=[]
    date=[]
    res = es.search(index="economy", body={"query": {"match_all": {}}})
    for hit in res['hits']['hits']:
        img="%(src)s"% hit["_source"]
        i="%(Title)s"% hit["_source"]
        t="%(Date)s"% hit["_source"]
        d="%(Content)s"% hit["_source"]
        image.append(img)
        tit.append(i)
        top.append(t)
        date.append(d)
        list=zip(image,top,date,tit)


    return render_template('economy.html', economy=list)


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        login_user(user, remember=form.remember.data)
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('build'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


    


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))




def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/img', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn



@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    comments=db.session.query(Comment).filter_by(user_id=current_user.id).all()
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form,comments=comments)




@app.route("/quiz", methods=["GET", "POST"])
def rating():  
    db.session.query(Profile).delete() 
    topic_list=['art','health','entertainment','sports','politics','society','economy','media','sci_tech','business','world','style']
    tab=[]
    top=[]
    tit=[]
    index=[]
    id=0
    i=len(topic_list)
    while i > 0:
        res = es.search(index=topic_list[i-1],
        body={"query": {"match_all": {}}})
        test=False
        for hit in res['hits']['hits']:
            while test==False:
                t="%(Title)s"% hit["_source"]
                tp="%(Topic)s"% hit["_source"]
                ids=str(id)
                tit.append(t)
                top.append(tp)
                index.append(ids)
                test=True
                id+=1
        i-=1
    tab=zip(index,top,tit)
    if request.method=="POST":
        db.session.query(Profile).delete()
        return render_template('recommendation.html')
    
    return render_template('quiz.html',tab=tab)


@app.route("/recommendation", methods=["GET", "POST"])
@login_required
def recommendation():
    if request.method == 'POST':
        #reading the original dataset
        Recommendation.query.filter_by(user_id=current_user.id).delete()
        table = request.form.getlist('choice')
        ARTICLES_READ=[]
        db.session.query(Profile).delete()
        for i in table:
            artcl = Profile(id=i, author=current_user)
            db.session.add(artcl)
            db.session.commit()

        ARTICLES_READ=[ int(x) for x in table ]
        article = pd.read_csv('ProcessedEnglish_news.csv')
        news_articles['index'] = list(range(len(news_articles.index)))
        news['index'] = list(range(len(news.index)))
        articles = news_articles['Content'].tolist()
        articles[0] #an uncleaned article
        cleaned_articles = list (map(clean_tokenize, articles[0:50]))
        cleaned_articles  #a cleaned, tokenized and stemmed article
        user_articles = ' '.join(cleaned_articles[i] for i in ARTICLES_READ)
        tfidf_matrix = TfidfVectorizer(stop_words='english', min_df=2)
        article_tfidf_matrix = tfidf_matrix.fit_transform(cleaned_articles)
        user_article_tfidf_vector = tfidf_matrix.transform([user_articles])
        user_article_tfidf_vector
        user_article_tfidf_vector.toarray()
        articles_similarity_score=cosine_similarity(article_tfidf_matrix, user_article_tfidf_vector)
        recommended_articles_id = articles_similarity_score.flatten().argsort()[::-1]
        final_recommended_articles_id = [article_id for article_id in recommended_articles_id 
        if article_id not in ARTICLES_READ ][:NUM_RECOMMENDED_ARTICLES]
        
        my_prediction1 = list(news.loc[news['index'].isin(final_recommended_articles_id)]['Title'])
        
        my_prediction3 = list(news.loc[news['index'].isin(final_recommended_articles_id)]['Date'])
        if(my_prediction1=="nan" or my_prediction1==""):
            my_prediction1=my_prediction2.split('.')[0]
        my_prediction2 = list(news.loc[news['index'].isin(final_recommended_articles_id)]['Content'])
        
        my_prediction=zip(my_prediction1,my_prediction2,my_prediction3)
        for a,b,c in my_prediction:
            recommend = Recommendation(title=a, content=b,date=c,author=current_user)
            db.session.add(recommend)
            db.session.commit()
        recommendations=db.session.query(Recommendation).filter_by(user_id=current_user.id).all()
        db.session.query(Profile).delete()

        
        return render_template('recommendation.html', recommendations = recommendations)
def similarity():
    Recommendation.query.filter_by(user_id=current_user.id).delete()
    ARTICLES_READ=[]
    table= [r.id for r in db.session.query(Profile.id)]
    ARTICLES_READ=[ int(x) for x in table ]
    article = pd.read_csv('ProcessedEnglish_news.csv')
    news_articles['index'] = list(range(len(news_articles.index)))
    news['index'] = list(range(len(news.index)))
    articles = news_articles['Content'].tolist()
    articles[0] #an uncleaned article
    cleaned_articles = list (map(clean_tokenize, articles[0:50]))
    cleaned_articles  #a cleaned, tokenized and stemmed article
    user_articles = ' '.join(cleaned_articles[i] for i in ARTICLES_READ)
    tfidf_matrix = TfidfVectorizer(stop_words='english', min_df=2)
    article_tfidf_matrix = tfidf_matrix.fit_transform(cleaned_articles)
    user_article_tfidf_vector = tfidf_matrix.transform([user_articles])
    user_article_tfidf_vector
    user_article_tfidf_vector.toarray()
    articles_similarity_score=cosine_similarity(article_tfidf_matrix, user_article_tfidf_vector)
    recommended_articles_id = articles_similarity_score.flatten().argsort()[::-1]
    final_recommended_articles_id = [article_id for article_id in recommended_articles_id 
    if article_id not in ARTICLES_READ ][:NUM_RECOMMENDED_ARTICLES]
    my_prediction1 = list(news.loc[news['index'].isin(final_recommended_articles_id)]['Title'])
    
    my_prediction3 = list(news.loc[news['index'].isin(final_recommended_articles_id)]['Date'])
    if(my_prediction1=="nan" or my_prediction1==""):            
        my_prediction1=my_prediction2.split('.')[0]
    my_prediction2 = list(news.loc[news['index'].isin(final_recommended_articles_id)]['Content'])
    my_prediction=zip(my_prediction1,my_prediction2,my_prediction3)
    for a,b,c in my_prediction:
        recommend = Recommendation(title=a, content=b,date=c,author=current_user)
        db.session.add(recommend)
        db.session.commit()
    
        

@app.route("/article/<int:recommendation_id>")
def article(recommendation_id):
    recommendation = Recommendation.query.get_or_404(recommendation_id)
    db.session.query(Profile).delete()
    article=Profile(id=recommendation_id,author=current_user)
    db.session.add(article)
    similarity()
    db.session.commit()
    return render_template('article.html', recommendations=recommendation)
@app.route("/latest_article/<int:latest_id>")
def latest(latest_id):
    similarity()
    latest = Latest.query.get_or_404(latest_id)
    db.session.query(Profile).delete()
    article=Profile(id=latest_id,author=current_user)
    db.session.add(article)
    db.session.commit()
    return render_template('latest_article.html', latest=latest)

@app.route('/prediction',methods=['POST','GET'])
def prediction():
    df= pd.read_csv("ProcessedEnglish_news.csv")
    df_data = df[["Title","Content","Topic"]]
    df_x = df_data['Content']
    df_y = df_data.Topic 
    corpus = df_x
    cv = CountVectorizer()
    #X = cv.fit_transform(corpus) # Fit the Data
    X= cv.fit_transform(df['Content'].values.astype('U'))
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(X, df_y, test_size=0.33, random_state=42)
    from sklearn.neighbors import KNeighborsClassifier
    clf = KNeighborsClassifier()
    clf.fit(X_train,y_train)
    clf.score(X_test,y_test)
    prediction1=''
    liste=[]
    if request.method == 'POST':
        comment = request.form['comment']
        data = [comment]
        vect = cv.transform(data).toarray()
        my_prediction = clf.predict(vect)
        def listToString(s):  
            str1 = " " 
            return (str1.join(s)) 
        
        prediction=listToString(my_prediction)
        prediction1=prediction.lower()
        if(prediction1=="sci-tech"):
            prediction1="sci_tech"
        tit=[]
        date=[]
        content=[]
        
        res = es.search(index=prediction1, body={"query": {"match_all": {}}})
        for hit in res['hits']['hits']:
            i="%(Title)s"% hit["_source"]
            t="%(Date)s"% hit["_source"]
            d="%(Content)s"% hit["_source"]
            tit.append(i)
            date.append(t)
            content.append(d)
            liste=zip(date,tit,content)
        comment = Comment(content=request.form['comment'], author=current_user,topic=prediction1)
        db.session.add(comment)
        db.session.commit()
        if(prediction1=="sci_tech"):
            prediction1="Science Technolgy"
    return render_template('result.html',prediction = prediction1,list=liste)

@app.route('/analize',methods=['POST','GET'])
def analize():
    df = pd.read_csv('ProcessedEnglish_news.csv')
    df["news"] = df["Title"].map(str) + \
                    df["Content"].map(str)
    df= df.drop("Title",axis=1)
    df= df.drop("Content",axis=1)
    from sklearn.model_selection import train_test_split
    y=df.Topic
    x=df.drop('Topic',axis=1)
    x_train,x_test,y_train,y_test=train_test_split(x,y,test_size=0.2)
    x_train.shape
    X_train = x_train['news'].to_list()
    X_test =x_test['news'].to_list()
    count_vect = CountVectorizer()
    x_train_counts = count_vect.fit_transform(X_train)
    # transform a count matrix to a normalized tf-idf representation (tf-idf transformer)
    tfidf_transformer = TfidfTransformer()
    x_train_tfidf = tfidf_transformer.fit_transform(x_train_counts)
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.pipeline import Pipeline
    knn = KNeighborsClassifier(n_neighbors=7)
    # training our classifier ; train_data.target will be having numbers assigned for each category in train data
    clf = knn.fit(x_train_tfidf,y_train)
    # Input Data to predict their classes of the given categories
    docs_new = ['need better representation female role models']
    # building up feature vector of our input
    x_new_counts = count_vect.transform(docs_new)
    # We call transform instead of fit_transform because it's already been fit
    x_new_tfidf = tfidf_transformer.transform(x_new_counts)
    import nltk
    from csv import DictReader
    import pickle 
    KnnML = open("knnModel.pkl","wb")
    pickle.dump(clf,KnnML)
    KnnML.close()
    classifier_model = open("knnModel.pkl","rb")
    new_model = pickle.load(classifier_model)
    user1=current_user.username.lower()
    es = Elasticsearch('http://localhost:9200')
    res = es.search(index=user1, body={"query": {"match_all": {}}})
    tweet=[]
    topic=[]
    for hit in res['hits']['hits']:
        text="%(text)s"% hit["_source"]
        x_new_counts = count_vect.transform([text])
        x_new_tfidf = tfidf_transformer.transform(x_new_counts)
        top= new_model.predict(x_new_tfidf)
        print(text,'==>',top)
        tweet.append(text)
        topic.append(top)
    features = list(zip (tweet, topic))
    tweetstopic = pd.DataFrame(features, columns=["tweet","topic"])
    from collections import Counter
    import numpy as np
    import matplotlib.pyplot as plt
    my_counter = Counter()
    for word in tweetstopic['topic'].values:
        my_counter.update(word)
    sub_cat_dict = dict(my_counter)
    sorted_sub_cat_dict = dict(sorted(sub_cat_dict.items(), key=lambda kv: kv[1]))
    ind = np.arange(len(sorted_sub_cat_dict))
    plt.figure(figsize=(20,5))
    p1 = plt.bar(ind, list(sorted_sub_cat_dict.values()))
    plt.ylabel('tweets')
    plt.title('% topic for each tweet ')
    plt.xticks(ind, list(sorted_sub_cat_dict.keys()))
    t=''
    k=0
    for i, j in sorted_sub_cat_dict.items():
        if j>k:
            k=j
            t=i
    interest1=t
    index1=t.lower()
    tit=[]
    date=[]
    content=[]
    if(index1=="sci-tech"):
        index1="sci_tech"
    result_dict = es.search(index=index1, body={"query": {"match_all": {}}})
    from pandasticsearch import Select
    health = Select.from_dict(result_dict).to_pandas()
    health.head()
    health.to_csv (r'index.csv', index = False, header=True)
    news_articles=pd.read_csv('index.csv')
    articles = news_articles['Content'].tolist()
    #Generate tfidf matrix model for entire corpus
    tfidf_matrix = TfidfVectorizer(stop_words='english', min_df=2)
    article_tfidf_matrix = tfidf_matrix.fit_transform(articles)
    interesttweets = tweetstopic[tweetstopic['topic'] == t]
    tweets = interesttweets['tweet'].tolist()
    usertweets = list (map(clean_tokenize, tweets[0:16]))
    #Generate tfidf matrix model for read articles
    user_article_tfidf_vector = tfidf_matrix.transform(usertweets)
    user_article_tfidf_vector.toarray()
    articles_similarity_score=cosine_similarity(article_tfidf_matrix, user_article_tfidf_vector)
    recommended_articles_id = articles_similarity_score.flatten().argsort()[::-1]
    news = health
    news['index'] = list(range(len(news.index)))
    liste=[]
    liste0=news.loc[news['index'].isin(recommended_articles_id)]['Title']
    liste1=news.loc[news['index'].isin(recommended_articles_id)]['Date']
    liste2=news.loc[news['index'].isin(recommended_articles_id)]['Content']
    liste=zip(liste0,liste1,liste2)
    if(index1=="sci_tech"):
        index1="Science Technology"
    return render_template('analize.html',index =index1,list=liste)

def scrapping():  
    link = "https://globalnews.ca/"
    test=True        
    with open('latest.csv','r') as read_obj:
        csv_dict_reader = DictReader(read_obj)
        link1 = ""
        for row in csv_dict_reader:
            title = getLastNewsTitle(link)
            a=row['Title']
            link2   =   getLastNews(link)
            content = getLastNewsContent(link2)
            d= row['Content']
            if(d==content) and (title==a):
                test=False
    if (test==True):
        link2   =   getLastNews(link)
        link1 = link2
        title = getLastNewsTitle(link)
        topic = getLastNewsTopic(link)
        date = getLastNewsDate(link)
        content = getLastNewsContent(link1)
        with open('latest.csv','a') as newFile:
            newFileWriter = csv.writer(newFile)
            newFileWriter.writerow([content, date,link,title,topic])
            latest=Latest(date=date,title=title,topic=topic,content=content)
            db.session.add(latest)
            db.session.commit()

def news_latest():
    with open('latest.csv', 'r') as read_obj:
        csv_dict_reader = DictReader(read_obj)
        topic=[]
        title=[]
        content=[]            
        date=[]
        href=[]
        for row in csv_dict_reader:
            d= row['Date']
            t=row['Title']
            tp=row['Topic']
            c=row['Content']
            h=row['Link']
            date.append(d)
            title.append(t)
            topic.append(tp)
            content.append(c)
            href.append(h)
        latest=list(zip(title,date,topic,content,href))
        df = pd.DataFrame(latest) 
        latst=df.iloc[[-1,-2,-3],[0,1,2,3,4]].values.tolist()
    return latst
        
@app.route("/latest")
def latest_article():
    latest = Latest.query.all()
    return render_template('latest.html', news=latest)

from threading import Timer
        
@app.route("/")
@app.route("/home")
def home():
    if current_user.is_authenticated:
        t = Timer(500.0, scrapping)
        t.start()
        latest=news_latest()
        recommendations=db.session.query(Recommendation).filter_by(user_id=current_user.id).all()
        return render_template('home.html',list=latest,recommendations=recommendations)
    else:
        with open('latest.csv', 'r') as read_obj:
            csv_dict_reader = DictReader(read_obj)
            topic=[]
            title=[]
            content=[]            
            date=[]
            href=[]
            for row in csv_dict_reader:
                d= row['Date']
                t=row['Title']
                tp=row['Topic']
                c=row['Content']
                h=row['Link']
                date.append(d)
                title.append(t)
                topic.append(tp)
                content.append(c)
                href.append(h)
            latest=list(zip(title,date,topic,content,href))
            df = pd.DataFrame(latest)
            for _ in range(10):
                value1 = randint(0, 10)
                value2 = randint(0, 10)
                value3 = randint(0, 10) 
            latst=df.iloc[[value1,value2,value3],[0,1,2,3,4]].values.tolist()
            return render_template('index.html',list=latst)
    
if __name__ == "__main__":
    app.run(debug=True)
    