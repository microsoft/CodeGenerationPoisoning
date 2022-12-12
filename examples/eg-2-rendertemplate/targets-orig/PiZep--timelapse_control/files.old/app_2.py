#!/bin/usr/env python3
# coding: utf-8

"""Main class of the application"""
from datetime import datetime, timedelta
import time
from importlib import import_module
import os
# import socket
from flask import Flask, render_template, Response
import tlconfig

# import camera driver
if os.environ.get('CAMERA'):
    print(os.environ.get('CAMERA'))
    Camera = import_module('camera_' + os.environ['CAMERA']).Camera
else:
    from camera import Camera

app = Flask(__name__)
last_shot = None
last_pic = None


@app.route('/')
def index():
    """Home and only page"""
    print("index")
    return render_template('index.html')


def gen(camera):
    """Video generator, stream for video True"""
    print("gen")
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Types: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed(video=True):
    """Video streaming route. Put it in the src attribute of an <img>"""
    print("video_feed")
    if video:
        cam = Camera()
        cam.perm_stream()
        return Response(gen(cam),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        cam.perm_stream()


def name_picture():
    """Set and return the name of a picture"""
    print("name_picture")
    return tlconfig.PATH


def take_picture():
    """Take a picture"""
    print("take_picture")
    cam = Camera()
    pic_full_path = name_picture()
    print(pic_full_path)
    res = tlconfig.CAM_RES
    cam.take_picture(pic_full_path, res)


def daysset():
    """Check that every days are set the same

    All values True or False means every day is set
    """
    print("daysset")
    return tlconfig.DAYS[1:] == tlconfig.DAYS[:-1]


def delay(self):
    """Calculate the delay in second before the next picture"""

    print("delay")
    next_pic = datetime.fromtimestamp(last_shot + tlconfig.INTERVAL)

    forecast = timedelta(hours=next_pic.hour,
                         minutes=next_pic.minute).total_seconds()
    limit = timedelta(hours=tlconfig.END_HOUR,
                      minutes=tlconfig.END_MIN).total_seconds()

    # Calculate next day if the next forecast picture
    # is taken after the limit hour
    week_day = next_pic.weekday()
    d_days = 0
    if forecast > limit:
        d_days += 1
        if not self.alldays:
            while not tlconfig.DAYS[week_day]:
                week_day = week_day + 1 if week_day < 6 else 0
                d_days += 1

        next_pic = datetime(year=last_shot.year, month=next_pic.month,
                            day=last_shot.day + d_days,
                            hour=tlconfig.START_HOUR,
                            minute=tlconfig.START_MIN)

    delay = next_pic - datetime.now()

    print(d_days, delay.total_seconds(), last_shot, next_pic)
    return delay.total_seconds()


def timelapse():
    """Set timelapse"""
    print("timelapse")
    global last_shot
    # global last_pic
    while True:
        last_shot = time.time()
        # last_pic = take_picture()
        if tlconfig.TIMESET:
            time.sleep(delay())
        else:
            time.sleep(tlconfig.INTERVAL - time.time() - last_shot)


if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True)

