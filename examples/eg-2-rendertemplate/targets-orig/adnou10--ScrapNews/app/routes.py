#import modules
from flask import render_template, redirect, flash, url_for, Response,request,render_template_string
from app import app 
#from app import q
import worker
from app.forms import URLForm
from app.models.article import Article
from app.scrap import Scrap as scr
from app.scrap import tojson as tjs
from rq.job import Job
from rq import Queue
from .tasks import scrap_and_save
from flask import jsonify
import json

q = Queue(connection=worker.conn)

#Home page that shows the 'get url' form
@app.route('/')
@app.route('/index')
def index():
    form=URLForm()
    return render_template('index.html', form=form)

#---------------------------------------------------------------------------------------------------------------------

#Api Page
@app.route("/apage/")
def Apage():
    #s='ok'
    return render_template('apage.html')

#------------------------------------ Background job for scraping --------------------------------------------------
# To catch url from form
@app.route('/start', methods=['POST'])
def get_art():
    url=request.form.get('url')
    # start job
    job = q.enqueue_call(
        func= scrap_and_save, args=(url,),result_ttl=500
    )
    # return created job id
    return redirect(url_for('result', job_key=job.id))

# Helper to get template and refresh
def get_template(template,data=[], refresh=False):
    return render_template(template, arts=data,nbr=len(data), refresh=refresh)



# Results
@app.route("/results/<job_key>", methods=['GET'])
def result(job_key):
    result=[]
    job = Job.fetch(job_key, connection=worker.conn)
    status = job.get_status()
    if status in ['queued', 'started', 'deferred', 'failed']:
        return get_template(template='articles.html',refresh=True)
    elif job.is_finished:
        result = job.result
        return get_template('articles.html',result)
    
    
#---------------------------------------------------------------------------------------------------------------------
# Articles  route
@app.route('/all')
@app.route('/articles')
def articles():
    arts=Article.objects()
    return  render_template('articles.html',arts=arts)   #display articles in db
    
    #return redirect(url_for('index'))
#---------------------------------------------------------------------------------------------------------------------

# To see article's detail 
@app.route("/disp/<id>") 
def display(id):
    art=Article.objects.get(id=id)
    return render_template('article.html',art=art)

#---------------------------------------------------------------------------------------------------------------------
# Search for articles by keyword
@app.route("/search",methods=['GET','POST'])
def key():
    if request.method == 'POST':
        key=request.form.get('key')
        arts=Article.objects(keywords=key)
        return  render_template('articles.html',arts=arts)   #display articles in db
    else:
        return redirect(url_for('articles'))
    
#---------------------------------------------------------------------------------------------------------------------
#api search by keyword
@app.route("/asearch",methods=['GET','POST'])
def asearch():
    if request.method == 'POST':
        key=request.form.get('key')
        return  redirect('/api/articles/'+key)   #display articles in db
    else:
        return redirect(url_for('articles'))       