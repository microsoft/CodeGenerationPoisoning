from flask import Flask, Blueprint, render_template, request
from flask_login import login_required, current_user
from flask_socketio import SocketIO, send

from app import app
from app.decorators import check_confirmed
from app.models import Student
import socket

bp = Blueprint('chat', __name__, template_folder='templates')
app.config['SECRET_KEY'] = 'mysecret'
socketio = SocketIO(app)


@bp.route('/test')
def test():
    return 'Chat test.'


@socketio.on('message')
def handle_message(msg):
    # print('Message: ' + msg)
    send(msg, broadcast=True)


@bp.route('/chat_page', methods=['GET', 'POST'])
@login_required
@check_confirmed
def chat_page():
    hostname = socket.gethostname()
    server = socket.gethostbyname(hostname)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('0.0.0.0', 0))
    port = sock.getsockname()[1]
    # server = server + ':' + str(port)
    server = '127.0.0.1:5000'
    remote_addr = request.remote_addr
    user = Student.get_full_info_by_id(current_user.id)
    return render_template('chat/chat.html', server=server, remote_addr=remote_addr, user=user, title=user.title)
