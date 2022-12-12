
from flask import Flask, send_from_directory
from flask_socketio import SocketIO, send, emit
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.api_core.datetime_helpers import DatetimeWithNanoseconds
import json
import uuid
import datetime

import sys
sys.path.append("back/")
from back.bot import Bot

"""
Server port is 5000 by default
"""

# Use a service account
cred = credentials.Certificate("/Users/nigelhuang/Desktop/moodverse-fdf22a769cc0.json")
firebase_admin.initialize_app(cred)

db = firestore.client()
app = Flask("moodverse")
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

msgs_ref = db.collection("messages")

bot1 = Bot("Bot 1")

@app.route("/") 
def root():
    return send_from_directory("./", "index.html")

"""
    Endpoint to get a json object of messages
"""
@app.route("/messages/b")
def messages():
    msgs = []
    for msg in msgs_ref.where(u"author_id", u"in", [u"Bob", u"bot1"]).order_by(u"sent").stream():
        t = msg.to_dict()
        exp = {
            "message_id": t["message_id"],
            "type": t["type"],
            "author_id": t["author_id"],
            "sent": t["sent"].rfc3339(),
            "body": t["body"]
        }
        msgs.append(exp)
    return json.dumps(msgs)

"""
  Used for message_id in database
"""
def get_uuid4():
    return str(uuid.uuid4())

"""
    Add a message to the database
"""
def add_message(msgDict):
    msg = {
        "message_id": get_uuid4(),
        "type": msgDict["type"],
        "author_id": msgDict["author_id"],
        "sent": firestore.SERVER_TIMESTAMP,
        "body": msgDict["body"]
    }
    print("Adding msg: {}".format(msg))
    msgs_ref.document(get_uuid4()).set(msg)

"""
    Stringify a msg dictionary and emit
"""
def send_message(msgDict):
    msgDict = json.dumps(msgDict)
    emit("message", msgDict)

"""
    Invoked when the user enters a message. Will send back a response from the model.
"""
@socketio.on("message")
def message_response(jsonData):
    jsonData = json.loads(jsonData)
    print("Recieved msg from {}".format(str(jsonData)))

    recievedMsg = {
        "message_id": get_uuid4(),
        "type": jsonData["type"],
        "author_id": jsonData["author_id"],
        "body": jsonData["body"]
    }

    add_message(recievedMsg)

    """
    Model response
    """

    model_response = bot1.get_response(recievedMsg["body"])
    print(model_response)
    msgPayload = {
        "message_id": get_uuid4(),
        "type": 1,
        "author_id": "bot1",
        "body": model_response
    }

    # msgPayload = {
    #     "message_id": get_uuid4(),
    #     "type": 1,
    #     "author_id": "bot1",
    #     "body": "I'm so sorry that you feel that way"
    # }

    add_message(msgPayload)

    send_message(msgPayload)

if __name__ == '__main__':
    socketio.run(app)