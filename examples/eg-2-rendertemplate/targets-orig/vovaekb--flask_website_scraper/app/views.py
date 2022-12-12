import os
from flask import Flask, request, render_template, send_file
from rq.job import Job
from rq import Queue
from app import app
from worker import conn
from app.scraper import scrape_website

q = Queue(connection=conn)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        job = q.enqueue_call(func=scrape_website, args=(url,), result_ttl=5000)
        return job.get_id()

    return render_template('index.html', results=results)


@app.route('/results/<job_key>', methods=['GET'])
def results(job_key):
    job = Job.fetch(job_key, connection=conn)

    if job.is_finished:
        if "error" in job.result:
            return str(job.result["error"])
        
        basedir = os.path.abspath(os.path.dirname(__file__))
        path = os.path.join(basedir, app.config['UPLOAD_FOLDER'], job.result)
        return send_file(path, as_attachment=True), 200
    else:
        return str(job.get_status()), 200
