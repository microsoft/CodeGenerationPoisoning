#!/usr/bin/env python3

import math
import os
import random
from hashlib import md5

import yaml
from celery import Celery, chord
from celery.utils.log import get_task_logger

from dropboxs3 import DBoxWorker
from dropboxs3 import S3Worker
from dropboxs3 import task_lock

celery_broker  = os.environ.get('CELERY_BROKER_URL', 'redis://localhost//')
celery_backend = os.environ.get('CELERY_BACKEND_URL', 'redis://localhost')

app = Celery('celery_runner', broker=celery_broker, backend=celery_backend)

app.conf.update(
    task_serializer='pickle',
    result_serializer='pickle',
    accept_content=['pickle'],
    enable_utc=True,
)


# import configs from YAML
try:
    with open("config.yml", "r") as config_file:
        yaml_config = yaml.load(config_file, Loader=yaml.Loader)
except Exception:
    # No yaml file? load from env instead
    print("Failed to find config.yml file in current dir, resorting to env vars instead")
    yaml_config    = None
    db_api         = os.environ.get('DB_API', False)
    s3_key         = os.environ.get('S3_KEY', False)
    s3_secret      = os.environ.get('S3_SECRET', False)
    s3_bucket      = os.environ.get('S3_BUCKET', False)
    s3_path        = os.environ.get('S3_PATH', False)


@app.task(bind=True, max_retries=2, name='migrate_all')
def migrate_all(self, local_db_api_key, s3_key_s, s3_secret_s, s3_bucket_s, s3_path_s, config_name=None):
    """
    given a dropbox api key, pulls a list of all files in Camera Uploads dir, and
    launches a celery group job to process all of them. Returns a sum of all processed
    files' sizes
    """
    tasklog = get_task_logger(__name__)

    # get a list of all files in this dropbox account's Camera Uploads folder
    if config_name:
        tasklog.info('Attempting to get list of images for config {}'.format(config_name))
    else:
        tasklog.info('Attempting to get list of images for API key {}'.format(local_db_api_key))
    try:
        db = DBoxWorker(db_api_key=local_db_api_key, auto_login=True)
        file_list = db.get_images()
        tasklog.debug('Got list of {} images for API key {}'.format(len(file_list.entries), local_db_api_key))
        if len(file_list.entries) == 0:
            return 0
    except Exception as exc:
        tasklog.error('migrate_all() failed to get files from DB: {}'.format(exc))
        self.retry(exc=exc, countdown=int(random.uniform(2, 4) ** self.request.retries))
        return 0

    # launch a chord
    try:
        chord([process_single_file.s(
            local_db_api_key, s3_key_s, s3_secret_s, s3_bucket_s, s3_path_s, x
        ) for x in file_list.entries], sum_bytes.s())()
        if config_name:
            tasklog.info('Chord launched for config {}'.format(config_name))
    except Exception as exc:
        tasklog.error('migrate_all() failed to start a chord for config {}: {}'.format(config_name, exc))
        self.retry(exc=exc, countdown=int(random.uniform(2, 4) ** self.request.retries))
    finally:
        if file_list and hasattr(file_list, 'entries'):
            return len(file_list.entries)
        else:
            return 0


@app.task(
    bind=True,
    name='process_single_file',
    rate_limit="4/m"
)
def process_single_file(self, db_api_s, s3_key_s, s3_secret_s, s3_bucket_s, s3_path_s, image):
    """
    given a dropbox API key and image, downlaods image and writes to S3, then deletes
    image from dropbox
    Atomic?
    We don't retry anything of the three non-atomic steps in this task. If the file remains in dropbox, a future
    migrate_all will retry it, until it's deleted.
    """
    tasklog = get_task_logger(__name__)

    task_id = '{}-{}-{}-{}'.format(db_api_s, s3_key_s, s3_secret_s, image.path_lower, app.oid)
    task_hash = md5(task_id.encode('utf-8')).hexdigest()

    with task_lock(task_hash) as lock_acquired:
        if not lock_acquired:
            tasklog.info('Failed to acquire LOCK {}'.format(task_id))
            return 0
        else:
            # download image from dropbox
            try:
                tasklog.debug('Getting file from dropbox {}'.format(image.path_lower))
                db = DBoxWorker(db_api_key=db_api_s, auto_login=True)
                m, f = db.get_file_from_dbox(image)
            except Exception as e:
                tasklog.warn('Failed to GET file from dropbox {} -- Exception: {}'.format(image.path_lower, e))
                return 0

            # upload to S3
            s3_path_for_file = "n/a"
            try:
                tasklog.debug('Uploading to S3 {}'.format(image.path_lower))
                s3_path_for_file = db.generate_s3_path_chunk(m)
                s3 = S3Worker(key=s3_key_s, secret=s3_secret_s, bucket=s3_bucket_s, path=s3_path_s, auto_login=True)
                s3.upload_to_s3(f, s3_path_for_file)
            except Exception as e:
                tasklog.warn('Failed to PUT file to S3 {} -- Exception: {}'.format(s3_path_for_file, e))
                return 0

            # delete image from dropbox
            try:
                tasklog.debug('Deleting from dropbox {}'.format(image.path_lower))
                db.delete_file_from_dbox(image)
                return m.size
            except Exception as e:
                tasklog.warn('Failed to DEL file from dropbox {} -- Exception: {}'.format(image.path_lower, e))
                # self.retry(countdown=2, exc=e, max_retries=1)
                return 0


@app.task(bind=True, name='sum_bytes')
def sum_bytes(self, args):
    return convert_size(sum(args))


def convert_size(size_bytes):
    """
    utility func for logging bytes transferred
    """
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])


def setup_celery_beats_scheduler():
    if not yaml_config:
        # only the beat scheduler has the config file mounted in docker-compose, workers can skip this
        # ToDo: is there a better way? To ID if im a worker or a beats scheduler?
        return
    dict_of_schedules = dict()

    for job in yaml_config['worker_configs']:
        # create a beat
        sched = {
                'task': 'migrate_all',
                'schedule': yaml_config['worker_configs'][job]['schedule'],
                'args': (yaml_config['worker_configs'][job]['db_api'],
                         yaml_config['worker_configs'][job]['s3_key'],
                         yaml_config['worker_configs'][job]['s3_secret'],
                         yaml_config['worker_configs'][job]['s3_bucket'],
                         yaml_config['worker_configs'][job]['s3_key_path'],
                         job)
            }
        dict_of_schedules['migrate_{}'.format(job)] = sched

    app.conf.beat_schedule = dict_of_schedules


def single_run():
    return migrate_all.delay(db_api, s3_key, s3_secret, s3_bucket, s3_path)


# run this on beats scheduler; fails silently on workers :/
setup_celery_beats_scheduler()
