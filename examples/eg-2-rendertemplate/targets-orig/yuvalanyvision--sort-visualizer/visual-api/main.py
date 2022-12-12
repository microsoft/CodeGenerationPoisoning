from flask import Flask, render_template
from flask_restful import Api
from flask_socketio import SocketIO, send, emit
from algorithms.algorithm_list import Algorithms
from algorithms.sort import Sort
from generator.number_generator import Generator
app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecret'
api = Api(app)
api.add_resource(Algorithms, '/algorithms')
api.add_resource(Generator, '/generate')
socketio = SocketIO()


@app.route('/')
def sessions():
    return render_template('session.html')


socketio.on_namespace(Sort('/sort'))

if __name__ == '__main__':
    socketio.init_app(app, cors_allowed_origins="*")
    socketio.run(app, host= '0.0.0.0', port=5000)
