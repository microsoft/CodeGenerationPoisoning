# project/server/main/views.py

import socket
import redis
from rq import Queue, Connection
from flask import render_template, Blueprint, jsonify, request, current_app, Response

from project.server.main.tasks import create_task
from project.server.models import Job

main_blueprint = Blueprint("main", __name__,)
host_name = socket.gethostname()
host_ip = socket.gethostbyname(host_name)


@main_blueprint.route("/", methods=["GET"])
def home():
    return render_template("main/home.html")


@main_blueprint.route("/config", methods=["GET"])
def get_config():
    return f"The Hostname of the container is: {host_name} and its IP is: {host_ip}"


@main_blueprint.route('/jobs', methods=['GET', 'POST'])
def get_enqueued_jobs():
    if request.method == 'GET':
        with Connection(redis.from_url(current_app.config["REDIS_URL"])):
            q = Queue()
            jobs = q.get_jobs()

        if jobs:
            response_object = {
                'status': 'success',
                'total_in_queue_jobs': len(q),
                'jobs': {index: str(job) for index, job in enumerate(jobs, 1)}
            }
        else:
            response_object = {
                'status': 'success',
                'queue_size': len(q)
            }
        return jsonify(response_object)

    if request.method == 'POST':
        graph = request.get_json()["graph"]

        with Connection(redis.from_url(current_app.config["REDIS_URL"])):
            q = Queue()
            task = q.enqueue(create_task, graph)

            job = Job(job_id=task.get_id(),
                      job_func_name=task.func_name,
                      job_status=task.get_status(),
                      job_result=task.result,
                      job_timeout=task.timeout,
                      job_is_queued=task.is_queued,
                      job_enqueued_at=task.enqueued_at,
                      job_is_finished=task.is_finished,
                      )
            job.save()

        response_object = {
            "status": "success",
            "data": {
                "task_id": task.get_id()
            }
        }
        return jsonify(response_object), 202


@main_blueprint.route("/jobs/<job_id>", methods=["GET"])
def get_enqueued_job(job_id):
    with Connection(redis.from_url(current_app.config["REDIS_URL"])):
        q = Queue()
        task = q.fetch_job(job_id)
    if task:
        response_object = {
            "status": "success",
            "data": {
                "task_id": task.get_id(),
                "task_status": task.get_status(),
                "task_result": task.result,
            },
        }
    else:
        response_object = {"status": "error"}
    return jsonify(response_object)


@main_blueprint.route("/jobs", methods=["GET"])
def get_jobs():
    jobs = Job.objects().to_json()
    return Response(jobs, mimetype="application/json", status=200)


@main_blueprint.route("/jobs/<job_id>", methods=["GET"])
def get_job(job_id):
    job = Job.objects.get(job_id=job_id).to_json()
    return Response(job, mimetype="application/json", status=200)


