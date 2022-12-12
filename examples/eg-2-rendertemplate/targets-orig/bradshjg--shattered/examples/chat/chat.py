import logging
from urllib.parse import parse_qsl

from flask import Flask, render_template, request, session
from shattered import Shattered

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

flask_app = Flask(__name__)
shattered_app = Shattered(host="rabbitmq")


@flask_app.route("/", methods=["GET", "POST"])
def chat():
    return render_template("chat.html")


@shattered_app.subscribe("/queue/chat")
def echo(headers, body, conn):
    data = dict(parse_qsl(body))
    email = data["email"]
    conn.send(body=f'<li>{email}: {data["message"]}</li>', destination="/topic/chat")
