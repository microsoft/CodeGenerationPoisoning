# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

# Flask stuffs
from flask import Flask, render_template, request, redirect, flash, url_for, session
# from flask_debugtoolbar import DebugToolbarExtension
# SQL stuffs
from flask_sqlalchemy import SQLAlchemy
# from sqlalchemy.ext.declarative import declarative_base
# Logging for Flask
import logging
from logging import Formatter, FileHandler
# Flask Login manager
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
# Flask AP Scheduler
from flask_apscheduler import APScheduler
# AI-TB
# from aitblib.basic import Basic
from aitblib import helpers
from aitblib import runners
from aitblib import enrichments
from aitblib import charting
from aitblib import ai
from aitblib.Flask_forms import LoginForm, RegisterForm, ForgotForm, SetupForm
# System
import os
from shutil import copyfile
import oyaml as yaml
import ccxt
from datetime import datetime
# Testing only
import sys


# Remember these two
# print('This is error output', file=sys.stderr)
# print('This is standard output', file=sys.stdout)

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#
# if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
# Init and config Flask
app = Flask(__name__)
app.config.from_pyfile('conf/flask.py')
app.config.from_pyfile('conf/db-default.py')

# Setup global variables
confPath = app.root_path + os.path.sep + 'conf' + os.path.sep
dataPath = app.root_path + os.path.sep + 'data' + os.path.sep
logPath = app.root_path + os.path.sep + 'logs' + os.path.sep
statPath = app.root_path + os.path.sep + 'static' + os.path.sep
upPath = app.root_path + os.path.sep + 'tmp' + os.path.sep + 'uploads' + os.path.sep

# Add custom Jinja2-filter


def ffname(text):
    return os.path.splitext(text)[0]


def u2d(utc):
    try:
        return datetime.utcfromtimestamp(int(utc) / 1000).strftime('%Y-%m-%d')
    except BaseException:
        return ''


app.add_template_filter(ffname)
app.add_template_filter(u2d)

# Custom DB setup
if os.path.exists(confPath + 'db.py'):
    app.config.from_pyfile('conf/db.py')

# Init and start Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Init SQLAlchemy
db = SQLAlchemy(app)

# Initialize SQLAlchemy Object


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)  # primary keys are required by SQLAlchemy
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))


# Add tables if not added
try:
    user = User.query.first()
except BaseException:
    # No tables found set them up!
    db.create_all()
    print('Setting up Tables...', file=sys.stderr)


# This needs to be here for flask-login to work
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Overwrite weird url for redirect Do Not Remove
@login_manager.unauthorized_handler
def unauthorized_callback():
    return redirect('/login')


# APScheduler
# Configuration Object
class ConfigAPS(object):
    SCHEDULER_API_ENABLED = True
    SCHEDULER_JOB_DEFAULTS = {
        'coalesce': True,
        'misfire_grace_time': 5,
        'max_instances': 1
    }


# Test Job
# if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
# Init Scheduler
scheduler = APScheduler()
# Config APS
app.config.from_object(ConfigAPS())
scheduler.init_app(app)

# Init used libraries
RunThe = runners.Runner(app.root_path, db)
AI = ai.AI(app.root_path, db)

# Data Download


@scheduler.task('interval', id='downData', seconds=30)
def downData():
    RunThe.dataDownload(True)


@scheduler.task('interval', id='upData', seconds=5)
def upData():
    RunThe.dataUpload()


@scheduler.task('interval', id='bkTest', seconds=5)
def bkTest():
    RunThe.backTest()

# Sentiment


@scheduler.task('cron', id='gTrend', hour='*')
def gTrend():
    RunThe.googleTrends()


@scheduler.task('cron', id='sentiRSS', hour='*')
def sentiRSS():
    RunThe.sentiRSS()

# Train AIs


@scheduler.task('interval', id='trainAI', seconds=15)
def trainAI():
    AI.trainANN()

# Minute by minute


@scheduler.task('cron', id='minuteJob', minute='*')
def minuteJob():
    # print('MinuteByMinute', file=sys.stdout)
    pass


# Hourly
# @scheduler.task('cron', id='hourlyjob', hour='*')
# def hourlyjob():
#     print('Hourly', file=sys.stdout)
# # Daily
# @scheduler.task('cron', id='dailyjob', day='*')
# def dailyjob():
#     print('Daily', file=sys.stdout)
# # Weekly
# @scheduler.task('cron', id='weeklyjob', week='*', day_of_week='sun')
# def weeklyjob():
#     print('Weekly', file=sys.stdout)
scheduler.start()

# Automatically tear down SQLAlchemy.


@app.teardown_request
def shutdown_session(exception=None):
    db.session.remove()


# Init Helper Class
do = helpers.Helper(app.root_path, db)
en = enrichments.Enrichment()
ch = charting.Chart(app.root_path, db)


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#

@app.route('/')
@login_required
def home():
    # Create files lists for config files
    dataCounts = {'con': len(do.listCfgFiles('conn')),
                  'data': len(do.listCfgFiles('data')),
                  'samples': len(do.listDataFiles('samples')),
                  'nuggets': len(do.listDataFiles('nuggets'))}
    # Render page
    return render_template('pages/home.html', dataCounts=dataCounts)


@app.route('/connections', methods=['GET', 'POST'])
@login_required
def connections():
    if request.method == 'POST':
        # Connection page wants something
        act = request.form['action']
        if act == 'add':
            # First page of adding Connection
            return render_template('pages/connections-add.html', action=act)
        if act == 'add2':
            # Second page of adding Connection
            mark = request.form['market']
            if mark == 'crypto':
                ex = ccxt.exchanges
                return render_template('pages/connections-add.html', action=act, market=mark, exch=ex, len=len(ex))
            if mark == 'forex':
                return render_template('pages/connections-add.html', action=act, market=mark)
        if act == 'fin':
            # Setup of exchange has finished create the connection
            ex = request.form['exchSel']
            market = request.form['market']
            if market == 'crypto':
                do.createCryptoCon(ex)
            return redirect("/connections")
        if act == 'info':
            # Create temp exchange instance based on post data
            ex = request.form['ex']
            return do.createCryptoInfo(ex)
        if act == 'fullinfo':
            con = request.form['con']
            # Create pathname and load connection config
            cfname = confPath + 'conn' + os.path.sep + con + '.yml'
            with open(cfname, 'r') as file:
                cfdata = yaml.full_load(file)
            # Create table in html
            cftable = "<table>"
            for key in cfdata:
                cftable = cftable + "<tr><th>" + str(key) + "</th><td>" + str(cfdata[key]) + "</td></tr>"
            cftable = cftable + "</table>"
            return cftable
        if act == 'delete':
            # Delete connection
            flash('Connection Deleted!', 'important')
            # Delete file
            delfile = confPath + 'conn' + os.path.sep + request.form['con'] + '.yml'
            os.remove(delfile)
            return redirect("/connections")

    else:
        connections = do.allCfgs('conn')
        return render_template('pages/connections.html', connections=connections)


@app.route('/data', methods=['GET', 'POST'])
@login_required
def data():
    if request.method == 'POST':
        # Data page wants something
        act = request.form['action']
        cons = do.listCfgFiles('conn')
        cons = list(map(lambda x: x.replace('.yml', ''), cons))
        if act == 'add':
            # Add data page
            return render_template('pages/data-add.html', cons=cons)
        if act == 'gitquotes':
            # Get a list of quotes available from selected connection
            con = request.form['con']
            # Return HTML for quote select box
            return do.gitCryptoQuotes(con)
        if act == 'gitpairs':
            # Get a list of pairs with the selected quote
            con = request.form['con']
            quote = request.form['quote']
            # Return HTML for pairs select box
            return do.gitCryptoPairs(con, quote)
        if act == 'fin':
            # Setup of data has finished create the data YAML
            con = request.form['conSel']
            quote = request.form['quoteSel']
            symb = request.form['symbSel']
            start = request.form['start']
            do.createCryptoData(con, quote, symb, start)
            return redirect("/data")
        if act == 'sample':
            # Setup of data has finished create the data YAML
            data = request.form['data']
            fromdate = request.form['fromdate']
            todate = request.form['todate']
            timeframe = request.form['timeframe']
            selection = request.form['selection']
            do.createSample(data, fromdate, todate, timeframe, selection)
            return redirect("/data")
        if act == 'delete':
            # Delete file
            delfile = confPath + 'data' + os.path.sep + request.form['id'] + '.yml'
            os.remove(delfile)
            return redirect("/data")
        if act == 'enable':
            id = request.form['id']
            # Read Config file
            dCfgFile = do.readCfgFile('data', id + '.yml')
            # Flip enabled if needed
            if request.form['status'] == 'true':
                dCfgFile['enabled'] = True
            else:
                dCfgFile['enabled'] = False
            do.writeCfgFile('data', id, dCfgFile)
            return redirect("/data")
        if act == 'delete-sample':
            # Delete file
            delfile = dataPath + 'samples' + os.path.sep + request.form['id'] + '.pkl'
            os.remove(delfile)
            return redirect("/data")
        if act == 'upload':
            id = request.form['id']
            # If no files sent
            if 'file' not in request.files:
                flash('No file part')
                return redirect(request.url)
            file = request.files['file']
            # If filename empty. User sent page with file
            if file.filename == '':
                flash('No selected file')
                return redirect(request.url)
            # Test secure filename
            filename = secure_filename(file.filename)
            # Split into filename and extension
            nom, ext = os.path.splitext(filename)
            # Save file
            file.save(upPath + id + ext)
            return 'Success'

    else:
        data = do.allCfgs('data')

        # List samples in folder ignoring .keep files
        samDatafiles = do.listDataFiles('samples')
        # Create data info array
        samples = []
        info = {}
        # Iterate through each file
        for dfile in samDatafiles:
            dstr = os.path.splitext(dfile)[0]
            parts = dstr.split('_')
            # print(parts,file=sys.stderr)
            info = {'id': dstr, 'con': parts[0], 'symb': parts[1] + '/' + parts[2], 'timeframe': parts[3], 'from': int(parts[4]), 'to': int(parts[5])}
            samples.append(info)
        return render_template('pages/data.html', data=data, samples=samples)


@app.route('/alchemy-enrich', methods=['GET', 'POST'])
@login_required
def alchemyenrich():
    if request.method == 'POST':
        # Data page wants something
        act = request.form['action']
        if act == 'add':
            # Add data page
            enlist = en.listIndi()
            return render_template('pages/alchemy-enrich-add.html', enlist=enlist)
        if act == 'fin':
            enname = request.form['enname']
            enriches = request.form['enriches']
            enstr = 'enname: ' + enname + "\n"
            enrichlist = []
            for item in request.form.getlist('enriches'):
                enrichlist.append(item)
            enstr = enstr + 'riches: ' + ', '.join(enrichlist) + "\n"
            enstr = enstr + 'total: ' + str(len(enrichlist)) + "\n"
            do.writeCfgFile('enrich', enname, enstr)
            return redirect("/alchemy-enrich")
        if act == 'delete':
            # Delete file
            delfile = confPath + 'enrich' + os.path.sep + request.form['enname'] + '.yml'
            os.remove(delfile)
            return redirect("/alchemy-enrich")
    else:
        enriches = do.allCfgs('enrich')
        return render_template('pages/alchemy-enrich.html', enriches=enriches)


@app.route('/alchemy-nugs', methods=['GET', 'POST'])
@login_required
def alchemynugs():
    if request.method == 'POST':
        # Data page wants something
        act = request.form['action']
        if act == 'add':
            samplist = do.listDataFiles('samples')
            samples = do.samplesInfo(samplist)
            enrichlist = do.listCfgFiles('enrich')
            enrichments = [os.path.splitext(x)[0] for x in enrichlist]
            depens = en.listDepen()
            nanas = en.listNaN()
            return render_template('pages/alchemy-nugs-add.html', samples=samples, enrichments=enrichments, depens=depens, nanas=nanas)
        if act == 'fin':
            sample = request.form['sample']
            indie = request.form['indie']
            depen = request.form['depen']
            nana = request.form['nana']
            do.createNugget(sample, indie, depen, nana)
            return redirect("/alchemy-nugs")
        if act == 'delete':
            # Delete file
            delfile = dataPath + 'nuggets' + os.path.sep + request.form['id'] + '.pkl'
            os.remove(delfile)
            return redirect("/alchemy-nugs")
    else:
        # List samples in folder ignoring .keep files
        nugfiles = do.listDataFiles('nuggets')
        # Pull nuggets info from above files
        nuggets = do.nuggetsInfo(nugfiles)
        return render_template('pages/alchemy-nugs.html', nuggets=nuggets)


@app.route('/observe', methods=['GET', 'POST'])
@login_required
def observe():
    if request.method == 'POST':
        # Observe page wants something
        act = request.form['action']
        nugget = request.form['nugget']
        if act == 'viewNug':
            script, div = ch.viewNugget(nugget)
        if act == 'viewCorr':
            script, div = ch.viewCorr(nugget)
        if act == 'viewFeat':
            script, div = ch.viewFeat(nugget)
        # List samples in folder ignoring .keep files
        nugfiles = do.listDataFiles('nuggets')
        # Pull nuggets info from above files
        nuggets = do.nuggetsInfo(nugfiles)
        return render_template('pages/observe.html', selected=nugget, nuggets=nuggets, script=script, div=div)
    else:
        # List nuggets in folder ignoring .keep files
        nugfiles = do.listDataFiles('nuggets')
        # Pull nuggets info from above files
        nuggets = do.nuggetsInfo(nugfiles)
        return render_template('pages/observe.html', nuggets=nuggets)


@app.route('/ai-ann', methods=['GET', 'POST'])
@login_required
def aiann():
    if request.method == 'POST':
        # ANN page wants something
        act = request.form['action']
        if act == 'add':
            # List nuggets in folder ignoring .keep files
            nugfiles = do.listDataFiles('nuggets')
            # Pull nuggets info from above files
            nuggets = do.nuggetsInfo(nugfiles)
            return render_template('pages/ai-ann-add.html', nuggets=nuggets)
        if act == 'fin':
            nugget = request.form['nugget']
            nom = request.form['nom']
            scaler = request.form['scaler']
            try:
                scarcity = request.form['scarcity']
            except BaseException:
                scarcity = "0"
            testsplit = request.form['testsplit']
            # Layers
            inputlayerunits = request.form['inputlayerunits']
            hiddenlayers = request.form['hiddenlayers']
            hiddenlayerunits = request.form['hiddenlayerunits']
            # Fitting
            optimizer = request.form['optimizer']
            loss = request.form['loss']
            metrics = request.form['metrics']
            batchsize = request.form['batchsize']
            epoch = request.form['epoch']
            do.createANN(nugget, nom, testsplit, scaler, scarcity, inputlayerunits, hiddenlayers, hiddenlayerunits, optimizer, loss, metrics, batchsize, epoch)
            return redirect("/ai-ann")
        if act == 'train':
            id = request.form['id']
            do.turnANNon(id)
            return redirect("/ai-ann")
        if act == 'delete':
            # Delete configuration files
            os.remove(confPath + 'aiann' + os.path.sep + request.form['id'] + '.yml')
            # Delete data files
            os.remove(dataPath + 'aiann' + os.path.sep + request.form['id'] + '.tf')
            os.remove(dataPath + 'aiann' + os.path.sep + request.form['id'] + '.pkl')
            os.remove(dataPath + 'aiann' + os.path.sep + request.form['id'] + '_sorted.pkl')
            # Delete static files
            os.remove(statPath + 'charts' + os.path.sep + request.form['id'] + '_acc.png')
            os.remove(statPath + 'charts' + os.path.sep + request.form['id'] + '_loss.png')
            return redirect("/ai-ann")
    else:
        anns = do.allCfgs('aiann')
        return render_template('pages/ai-ann.html', anns=anns)


@app.route('/sent-rss', methods=['GET', 'POST'])
@login_required
def sentrss():
    if request.method == 'POST':
        # Sent RSS page wants something
        act = request.form['action']
        if act == 'add':
            return render_template('pages/sent-rss-add.html')
        if act == 'fin':
            do.createRSSFeed(request.form.to_dict())
            return redirect("/sent-rss")
        if act == 'delete':
            # Delete configuration file
            os.remove(confPath + 'sentrss' + os.path.sep + request.form['id'] + '.yml')
            return redirect("/sent-rss")
        if act == 'enable':
            id = request.form['id']
            # Read Config file
            dCfgFile = do.readCfgFile('sentrss', id + '.yml')
            # Flip enabled if needed
            if request.form['status'] == 'true':
                dCfgFile['enabled'] = True
            else:
                dCfgFile['enabled'] = False
            do.writeCfgFile('sentrss', id, dCfgFile)
            return redirect("/sent-rss")
    else:
        rssfeeds = do.allCfgs('sentrss')
        return render_template('pages/sent-rss.html', rssfeeds=rssfeeds)


@app.route('/sent-trend', methods=['GET', 'POST'])
@login_required
def senttrend():
    if request.method == 'POST':
        # Sent RSS page wants something
        act = request.form['action']
        if act == 'add':
            return render_template('pages/sent-trend-add.html')
        if act == 'fin':
            do.createGoogleTrend(request.form.to_dict())
            return redirect("/sent-trend")
        if act == 'delete':
            # Delete configuration file
            os.remove(confPath + 'senttrend' + os.path.sep + request.form['id'] + '.yml')
            return redirect("/sent-trend")
        if act == 'enable':
            id = request.form['id']
            # Read Config file
            dCfgFile = do.readCfgFile('senttrend', id + '.yml')
            # Flip enabled if needed
            if request.form['status'] == 'true':
                dCfgFile['enabled'] = True
            else:
                dCfgFile['enabled'] = False
            do.writeCfgFile('senttrend', id, dCfgFile)
            return redirect("/sent-trend")
    else:
        trends = do.allCfgs('senttrend')
        return render_template('pages/sent-trend.html', trends=trends)


@app.route('/sent-twit', methods=['GET', 'POST'])
@login_required
def senttwit():
    if request.method == 'POST':
        # Sent RSS page wants something
        act = request.form['action']
        if act == 'add':
            return render_template('pages/sent-twit-add.html')
        if act == 'fin':
            do.createTwitterFeed(request.form.to_dict())
            return redirect("/sent-twit")
        if act == 'delete':
            # Delete configuration file
            os.remove(confPath + 'senttwit' + os.path.sep + request.form['id'] + '.yml')
            return redirect("/sent-twit")
    else:
        twitfeeds = do.allCfgs('senttwit')
        return render_template('pages/sent-twit.html', twitfeeds=twitfeeds)


@app.route('/sent-nlp', methods=['GET', 'POST'])
@login_required
def sentnlp():
    if request.method == 'POST':
        # Sent NLP page wants something
        act = request.form['action']
        if act == 'changeAI':
            sentai = do.readCfgFile('sentnlp', 'sent-ai.yml')
            sentai['ai'] = request.form['ai']
            do.writeCfgFile('sentnlp', 'sent-ai', sentai)
            return redirect("/sent-nlp")
    else:
        sentai = do.readCfgFile('sentnlp', 'sent-ai.yml')
        return render_template('pages/sent-nlp.html', ai=sentai)


@app.route('/backtest', methods=['GET', 'POST'])
@login_required
def backt():
    if request.method == 'POST':
        # ANN page wants something
        act = request.form['action']
        if act == 'add':
            # List data in folder ignoring .keep files
            datafiles = do.listCfgFiles('data')
            aifiles = do.listCfgFiles('aiann')
            enfiles = do.listCfgFiles('enrich')
            return render_template('pages/backtest-add.html', datas=datafiles, ais=aifiles, ens=enfiles)
        if act == 'fin':
            do.createBacktest(request.form.to_dict())
            return redirect("/backtest")
        if act == 'run':
            id = request.form['id']
            do.turnBTon(id)
            return redirect("/backtest")
        if act == 'delete':
            # Delete configuration file
            os.remove(confPath + 'bt' + os.path.sep + request.form['id'] + '.yml')
            # Delete data files
            os.remove(dataPath + 'bt' + os.path.sep + request.form['id'] + '.py')
            os.remove(dataPath + 'bt' + os.path.sep + request.form['id'] + '_entry.pkl')
            os.remove(dataPath + 'bt' + os.path.sep + request.form['id'] + '_native.pkl')
            if os.path.exists(dataPath + 'bt' + os.path.sep + request.form['id'] + '_results.csv'):
                os.remove(dataPath + 'bt' + os.path.sep + request.form['id'] + '_results.csv')
            if os.path.exists(dataPath + 'bt' + os.path.sep + request.form['id'] + '_exit.pkl'):
                os.remove(dataPath + 'bt' + os.path.sep + request.form['id'] + '_exit.pkl')
            # Delete static files
            if os.path.exists(statPath + 'bt' + os.path.sep + request.form['id'] + '_chart.html'):
                os.remove(statPath + 'bt' + os.path.sep + request.form['id'] + '_chart.html')
            if os.path.exists(statPath + 'bt' + os.path.sep + request.form['id'] + '_report.html'):
                os.remove(statPath + 'bt' + os.path.sep + request.form['id'] + '_report.html')
            return redirect("/backtest")
    else:
        bktests = do.allCfgs('bt')
        return render_template('pages/backtest.html', bktests=bktests)


@app.route('/trading')
@login_required
def trading():
    return render_template('pages/trading.html')


@app.route('/ops-db')
@login_required
def opsdb():
    return render_template('pages/ops-db.html')


@app.route('/ops-run')
@login_required
def opsrun():
    runners = {'Data Downloader (Aggressive)': 'dataDownloadAggro.log',
               'Data Uploader': 'dataUpload.log',
               'ANN Training': 'trainANN.log'}
    return render_template('pages/ops-run.html', runners=runners)


@app.route('/ops-users')
@login_required
def opsusers():
    return render_template('pages/ops-users.html')


@app.route('/changelogs')
@login_required
def changelogs():
    return render_template('pages/changelogs.html')


# ----------------------------------------------------------------------------#
# Login and Registration Templates
# ----------------------------------------------------------------------------#

# User templates
@app.route('/login', methods=['GET', 'POST'])
def login():
    logform = LoginForm()
    name = request.form.get('name')
    # email = request.form.get('email')
    password = request.form.get('password')
    # remember = True if request.form.get('remember') else False
    if logform.validate_on_submit():
        # Check for existence of username
        user = User.query.filter_by(name=name).first()
        # Check if user actually exists and then
        # take the user supplied password, hash it, and compare it to the hashed password in database
        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.')
            return redirect(url_for('login'))  # if user doesn't exist or password is wrong, reload the page
        login_user(user)
        return redirect(url_for('home'))
    return render_template('forms/login.html', form=logform)


@app.route("/logout")
def logout():
    # Clear flashes
    session.pop('_flashes', None)
    logout_user()
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        # Get variables
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        # Check for existsing user and push back to register page if exists
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Please check your login details and try again.')
            return redirect(url_for('register'))
        # Create a new user object of User with the above data
        new_user = User(email=email, name=name, password=generate_password_hash(password, method='sha256'))
        # Add this new user to the database
        db.session.add(new_user)
        db.session.commit()
        # Form finished successfully go to login
        return redirect('/login')
    return render_template('forms/register.html', form=form)


@app.route('/forgot')
def forgot():
    form = ForgotForm(request.form)
    return render_template('forms/forgot.html', form=form)


# Log streamer
@app.route('/logstream/<alog>')
@login_required
def logstream(alog):
    def generate(alog):
        with open(logPath + alog) as f:
            yield f.read()
    if os.path.exists(logPath + alog):
        return app.response_class(generate(alog), mimetype='text/plain')
    else:
        return 'Log file empty...'

# Setup


@app.route('/setup', methods=['GET', 'POST'])
def syssetup():
    form = SetupForm()
    if form.validate_on_submit():
        # Get variables
        dbtype = request.form.get('dbtype')
        hostname = request.form.get('hostname')
        database = request.form.get('database')
        uname = request.form.get('uname')
        password = request.form.get('password')
        # Create connection string
        conString = "SQLALCHEMY_DATABASE_URI = '" + dbtype + '://' + uname + ':' + password + '@' + hostname + '/' + database + "'"
        # Write to file
        with open(confPath + 'db.py', 'w') as f:
            f.write(conString)
        app.config.from_pyfile('conf/db.py')
        # Form finished successfully go to login
        return redirect('/setup')
    return render_template('forms/setup.html', form=form)

# Error handlers.


@app.errorhandler(500)
def internal_error(error):
    # db_session.rollback()
    return render_template('errors/500.html'), 500


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')


# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':

    # Init debugger
    # toolbar = DebugToolbarExtension(app)
        # Overwrite config for flask-debugtoolbar
    # app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
    app.config['DEBUG'] = True
    app.config['UPLOAD_FOLDER'] = 'tmp'
    # Clear down all current run locks
    do.clearRunLocks()
    # Logging options DEBUG INFO WARNING ERROR CRITICAL
    # app.logger.setLevel(logging.CRITICAL)
    logging.getLogger('apscheduler').setLevel(logging.ERROR)
    # Create NLP configs if they don't exist
    if not os.path.exists(confPath + 'sentnlp' + os.path.sep + 'sent-ai.yml'):
        copyfile(confPath + 'sentnlp' + os.path.sep + 'sent-ai-def.yml', confPath + 'sentnlp' + os.path.sep + 'sent-ai.yml')
    # Run App
    # app.run(use_reloader=False) # threaded=False breaks APScheduler

    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
