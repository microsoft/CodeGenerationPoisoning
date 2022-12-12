from multiprocessing import Process
from flask_socketio import SocketIO, emit
from flask import Flask, render_template, jsonify
import time
import zmq

context = zmq.Context()

api_socket = context.socket(zmq.REQ)
api_socket.connect("tcp://localhost:3001")


app = Flask(__name__)
app.config['SECRET_KEY'] = '5b6db414d4fd764a'
socketio = SocketIO(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api')
def api():
    api_socket.send(b'Request')
    return api_socket.recv()


@app.route('/log')
def log():
    return "This is where the log will be!"


@socketio.on('connected')
def connected():
    api_socket.send(b'Request')
    res = api_socket.recv()
    res = res.decode('utf-8')
    emit('data', res)


def listener():
    update_socket = context.socket(zmq.REP)
    update_socket.connect("tcp://localhost:3002")
    while True:
        res = update_socket.recv()
        socketio.emit('data', res, broadcast=True)
        update_socket.send(b'Recieved')


def main():
    updates_listener = Process(target=listener)
    updates_listener.start()
    socketio.run(app, host='0.0.0.0', port=3000, debug=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        updates_listener.join()


if __name__ == "__main__":
    main()
