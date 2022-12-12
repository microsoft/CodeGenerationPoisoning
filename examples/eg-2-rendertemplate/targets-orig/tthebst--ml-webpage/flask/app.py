import docker
from flask import jsonify
from flask import Flask, request
from flask import render_template
import requests
import os
import scipy
import urllib.request
import json
import tempfile
import soundfile as sf

app = Flask(__name__)


@app.route("/")
def home():

    return render_template("home.html")


@app.route("/about")
def about():

    return render_template("about.html")


@app.route("/classification", methods=["GET", "POST"])
def classification():

    if request.method == "POST":

        imfile = request.files["photo"]

        imfile.save("hallo.jpg")

    return render_template("classification.html")


@app.route("/object_detect", methods=["GET", "POST"])
def object_detect():

    return render_template("object_detect.html")


@app.route("/language", methods=["GET", "POST"])
def language():

    return render_template("language.html")


@app.route("/generative", methods=["GET", "POST"])
def generative():

    class_idx = json.loads(
        urllib.request.urlopen(
            "https://s3.amazonaws.com/deep-learning-models/image-models/imagenet_class_index.json"
        ).read()
    )
    label = [class_idx[str(k)][1] for k in range(len(class_idx))]
    idx = [k for k in range(len(class_idx))]

    return render_template("generative.html", label=label, idx=idx)


@app.route("/generative/biggan", methods=["GET", "POST"])
def generative_biggan():
    print("got post to bgigan")
    print(request.data)
    # client = docker.DockerClient()
    # container = client.containers.get("generative")
    # ip_add = container.attrs['NetworkSettings']['IPAddress']
    resp = requests.post(
        "https://generative-ch3s33ctwq-ez.a.run.app/biggan", data=request.data, verify=False
    )

    print(resp.json())
    return (resp.text, resp.status_code, resp.headers.items())


@app.route("/language/transformer", methods=["GET", "POST"])
def transformer():
    print("got post to bgigan")
    print(request.data)
    # client = docker.DockerClient()
    # container = client.containers.get("language")
    # print(container)
    # ip_add = container.attrs['NetworkSettings']['IPAddress']
    # print(ip_add)
    resp = requests.post(
        "https://language-ch3s33ctwq-ez.a.run.app/en2de", data=request.data, verify=False
    )

    return (resp.text, resp.status_code, resp.headers.items())


@app.route("/language/deepspeech", methods=["GET", "POST"])
def deepspeech():
    print("got post to bgigan")
    print(request.data)
    # client = docker.DockerClient()
    # container = client.containers.get("language")
    # ip_add = container.attrs['NetworkSettings']['IPAddress']
    resp = requests.post(
        "https://language-ch3s33ctwq-ez.a.run.app/deepspeech_transcribe",
        data=request.data,
        files=request.files,
        verify=False,
    )

    return (resp.text, resp.status_code, resp.headers.items())


if __name__ == "__main__":
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    app.run(port=5000, debug=True, host="0.0.0.0")
