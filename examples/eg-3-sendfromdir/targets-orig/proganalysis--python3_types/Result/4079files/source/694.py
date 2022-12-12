from datetime import datetime
from flask import render_template, send_from_directory, Response, redirect, jsonify, session, request, abort

from waveDIM import app
import waveDIM.controllers.shoutcast as shoutcast
from waveDIM import stream_factory
from settings import streams

__author__ = "Sander Ferdinand"


@app.route("/")
def index():
    if not session.get("wishlist", ""):
        session["wishlist"] = []
    return render_template("live.html", streams=streams)


@app.route("/api/wishlist", methods=["GET", "POST"])
def wishlist():
    # if not session.get("wishlist", ""):
    #     session["wishlist"] = []
    #
    # if request.method == "POST":
    #
    #     return jsonify({"status": "OK"})
    # elif request.method == "GET":
    #     return jsonify({"data": session["wishlist"]})
    pass


@app.route("/api/metadata")
def metadata():
    data = {}

    for stream_id, _data in streams.items():
        data[stream_id] = _data

        for stream_url, _metadata in shoutcast.METADATA.items():
            if _data["stream"] == stream_url:
                data[stream_id]["metadata"] = _metadata

    return jsonify(data)


@app.route("/stream/<path:path>")
def proxyradio(path):
    """Javascript cannot fetch remote audio
    streams without proper CORS headers due
    to security restrictions imposed by the
    browser. Proxy instead."""
    if path not in streams:
        return "radio not found"

    radio = streams[path]
    response = shoutcast.get(radio["stream"])
    return Response(response=shoutcast.iter_content(response),
                    content_type=response.headers['Content-Type'])


@app.route('/static/<path:path>')
def static(path):
    return send_from_directory('static', path)


@app.route("/favicon.ico")
def ico():
    return ""


@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r


# @app.route('/w')
# def proxy_stream():
#     stream_url = "http://icecast.omroep.nl/radio1-bb-mp3"
#     plexer = stream_factory(stream_url).get_stream()
#     response = shoutcast.get(stream_url)
#     return Response(response=shoutcast.iter_content(response),
#                     content_type=response.headers['Content-Type'])