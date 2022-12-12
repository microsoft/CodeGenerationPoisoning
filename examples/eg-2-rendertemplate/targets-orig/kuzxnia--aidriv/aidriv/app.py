from gevent import monkey
monkey.patch_all()

import cv2
from flask import (Flask, Response, render_template, send_file,
                   stream_with_context)
from flask_sockets import Sockets
from camera import Camera
from steering import Steering
from gevent import spawn, sleep

app = Flask(__name__, static_folder='static')
sockets = Sockets(app)
steering = Steering()
camera = Camera()

#creating greenthread for getting frames from camera
spawn(camera.get_frames)

def generate(cam):
    while True:
        if cam.frame is None:
            sleep(0)
            continue

        (flag, encodedImage) = cv2.imencode(".jpg", cam.frame)
        cam.frame = None

        # ensure the frame was successfully encoded
        if not flag:
            continue

        print('yield')
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
            bytearray(encodedImage) + b'\r\n')
        
        sleep(0.02)


@sockets.route('/echo')
def echo_socket(ws):
    while not ws.closed:
        message = ws.receive()
        forward, turn = message.split()
        steering.change_motors_speed(int(forward), int(turn))
    steering.change_motors_speed(0, 0)


@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')


@app.route("/<path:path>")
def static_files(path):
    return send_file(path)


@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(generate(camera), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler

    server = pywsgi.WSGIServer(('0.0.0.0', 8000), app, handler_class=WebSocketHandler)
    server.serve_forever()