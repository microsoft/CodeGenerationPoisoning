from flask import Flask, request, abort , send_from_directory

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

import requests
from firebase import firebase
from datetime import datetime
from test_fuzzy import match_tracking_menu
from Flexmessage.TrackingMessage import create_message
from Flexmessage.ImgMap import Create_ImgMap_AllProvider , Create_ImgMap_ChooseProvider

app = Flask(__name__)
from config import channel_access_token , channel_secret , DATABASE_URL , RICHMENU_ID
line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)
firebase = firebase.FirebaseApplication(DATABASE_URL, None)
DATABASE_NAME = "TRACKING_HISTORY"

import os
@app.route("/ImgMap/<picname>/1040")
def serve_imagemap_chooseprovider(picname):
    # Handle the request and send the requested file. To locate the file, use the secure built-in Flask method 
    current_file_folder = os.path.dirname(os.path.realpath(__file__)) #get directory path ของไฟล์นี้
    print(current_file_folder)
    image_folder = os.path.join(current_file_folder,"Flexmessage")
    print(image_folder)

