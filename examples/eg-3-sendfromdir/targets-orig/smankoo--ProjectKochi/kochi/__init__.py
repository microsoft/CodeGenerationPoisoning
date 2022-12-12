from __future__ import unicode_literals
import youtube_dl
import uuid
import os
import json
import sys
import time
import shutil
import datetime

from flask import Flask, render_template, request, redirect, send_from_directory, url_for, Response, jsonify
from slugify import slugify

import time
import atexit

from rq import Queue
from rq.job import Job
import rq_dashboard

from kochi.worker import conn
from kochi.worker import redis_url
from kochi.utils import MyLogger
from kochi.utils import _youtubedl_progress_hook
from kochi.utils import make_archive
from kochi.utils import _youtubedl
from kochi.utils_aws import get_s3_download_url


my_path = os.path.abspath(os.path.dirname(__file__))
config_loc = os.path.join(my_path, "../config.json")

with open(config_loc, 'r') as config_file:
    data = config_file.read()

config = json.loads(data)


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.route('/', methods=['POST', 'GET'])
    def index():
        return(render_template('index.html'))

    @app.route('/test')
    def test():
        return render_template('test.html')

    @app.route('/_download/<string:req_type>', methods=['GET', 'POST'])
    def download(req_type="single"):
        download_parent = config['download_dir']
        cachedir = config['cache_dir']
        downloadid = uuid.uuid4().hex

        downloaddir = download_parent + '/' + downloadid

        if not os.path.exists(cachedir):
            os.makedirs(cachedir)

        if not os.path.exists(downloaddir):
            os.makedirs(downloaddir)

        if request.method == 'GET':

            if req_type.lower() == "single":
                url = request.args.get('url')

                if url is None or url == "":
                    return jsonify({"error": "empty URL passed"})

                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '320',
                        },
                        {'key': 'FFmpegMetadata'},
                    ],
                    'logger': MyLogger(),
                    'progress_hooks': [my_hook],
                    'outtmpl': downloaddir + '/%(title)s.%(ext)s',
                }

                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                    ydl_info = ydl.extract_info(url, download=False)

                if len(os.listdir(downloaddir)) == 1:
                    return jsonify({"downloadid": downloadid, "ydl_info": ydl_info})
                else:
                    raise "Invalid number of files in downloaddir"

    @app.route('/api/getfile/<string:download_id>')
    def get_file(download_id):
        # downloadid = request.args.get('downloadid')
        downloaddir = os.path.join(config['download_dir'], download_id)
        if len(os.listdir(downloaddir)) == 1:
            file_name = os.listdir(downloaddir)[0]
            return send_from_directory(downloaddir, file_name, as_attachment=True)

    def my_hook(d):
        # download_perc = round(d['downloaded_bytes']*100 / d['total_bytes'])
        # if download_perc > 30:
        #     print("download_perc:" + download_perc)
        pass

    @app.route('/_getprogress')
    def progress():
        download_perc = 0
        data = "perc:" + str(download_perc) + "\n\n"
        print(data)

        # return Response(data, mimetype= 'text/event-stream')
        return jsonify({"perc": download_perc})

    @app.route('/cleanup')
    def cleanup():
        download_parent = config['download_dir']
        if not os.path.isdir(download_parent):
            return([])
        delete_list = []
        for file_name in os.listdir(download_parent):
            # delete directories older than 2 minutes
            d = os.path.join(download_parent, file_name)
            if file_name != config['cache_dir'] \
                    and os.path.isdir(d)       \
                    and os.stat(d).st_mtime < (time.time() - (30*60)):
                delete_list.append(d)
                shutil.rmtree(d)

        return(json.dumps(delete_list))

    @app.route('/_getplaylistitems', methods=['POST', 'GET'])
    def get_playlist_items():
        # url = "https://music.youtube.com/playlist?list=OLAK5uy_m_Kjhx3wck_RmcJuPf0kLR60t4hpP65Pc"
        url = request.args.get('url')

        print("Received Playlist URL is: " + url)

        ydl_opts = {}
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl_info = ydl.extract_info(url, download=False)

        return ydl_info
        # return render_template('index.html', ydl_info=ydl_info)

    @app.template_filter('sec_to_time')
    def sec_to_time(sec):
        return str(datetime.timedelta(seconds=sec))


#################

    # Views

    # set default settings for rq-dashboard
    app.config.from_object(rq_dashboard.default_settings)
    # Set URL of Redis server being used by Redis Queue
    app.config.update(RQ_DASHBOARD_REDIS_URL=redis_url)
    # Register flask blueprint with prefix /rqstatus
    app.register_blueprint(rq_dashboard.blueprint, url_prefix="/rqstatus")

    @app.route('/api/trigger_download', methods=['POST'])
    def trigger_download():
        retdata = {}

        list_name = request.json.get('list_name')
        url_list = request.json.get('url_list')

        q = Queue(connection=conn)
        job_id = str(uuid.uuid4().hex)
        job = q.enqueue(_youtubedl, job_id, list_name, url_list,
                        config, job_id=job_id, description=list_name,
                        job_timeout='10m')
        # _youtubedl(job_id, list_name, url_list)

        download_id = str(job_id)
        retdata['download_id'] = download_id

        return retdata

    @app.route('/api/get_download_status', methods=['POST'])
    def get_download_status():
        retdata = {}

        download_id = request.json.get('download_id')

        job = Job.fetch(download_id, connection=conn)
        job_status = job.get_status()

        retdata['job_status'] = job_status

        if job_status == "finished":
            retdata['download_url'] = _get_download_url(download_id)

        return retdata

    def _get_download_url(download_id):
        # donwload_url = url_for('get_file', download_id=download_id, _external=True)
        download_url = get_s3_download_url(download_id)
        return download_url


################

    return app
