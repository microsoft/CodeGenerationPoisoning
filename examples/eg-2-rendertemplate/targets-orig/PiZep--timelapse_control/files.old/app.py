#!/usr/bin/env python
"""Main app"""
from importlib import import_module
import os
from flask import Flask, render_template, Response

# import camera driver
if os.environ.get('CAMERA'):
    print(os.environ.get('CAMERA'))
    Camera = import_module('camera_' + os.environ['CAMERA']).Camera
else:
    from camera import Camera

# Raspberry Pi camera module (requires picamera package)
# from camera_pi import Camera

app = Flask(__name__)


@app.route('/')
def index():
    """Video streaming home page."""
    print("index")
    return render_template('index.html')


def gen(camera):
    """Video streaming generator function."""
    print("gen")
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed(video=True):
    """Video streaming route. Put this in the src attribute of an img tag."""
    print("video_feed")
    if video:
        cam = Camera()
        cam.perm_stream()
        return Response(gen(cam),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        cam.perm_stream()
        # return None


if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True)

