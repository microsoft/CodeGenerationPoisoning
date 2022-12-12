#!/usr/bin/env python
from importlib import import_module
import os
from flask import Flask, render_template, Response
from flask import send_file
# import camera driver

# from camera import Camera


from .camera_opencv import Camera

# Raspberry Pi camera module (requires picamera package)
# from camera_pi import Camera

app = Flask(__name__)


@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')


def gen(camera):
    """Video streaming generator function."""
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/static/<path:location>', methods=['GET'])
def handle_static(location):
    return send_file(os.path.abspath(os.path.join('static', os.pardir)) + '/static/' + location,
                     mimetype='image/png')


if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True, debug=True)
