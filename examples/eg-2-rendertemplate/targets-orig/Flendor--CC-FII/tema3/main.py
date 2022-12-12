import io

from flask import Flask, render_template, request, flash, redirect, send_file, session
import pyrebase
from google.auth import *
from google.oauth2 import service_account
from google.cloud import speech_v1p1beta1
from google.cloud.speech_v1p1beta1 import enums
from google.cloud import texttospeech
from google.cloud.texttospeech import types
from google.cloud import datastore
import json
import os
import urllib
from urllib import request as req
import firebase_admin
from firebase_admin import credentials
from firebase_admin import storage
from firebase_admin import auth
import time
import datetime

app = Flask(__name__)

app.secret_key = b""
app.permanent_session_lifetime = datetime.timedelta(days=365)

with open("firebaseConfig.json", "r") as f:
    content = f.read()
firebaseConfig = json.loads(content)
firebase = pyrebase.initialize_app(firebaseConfig)
firebase_auth = firebase.auth()
firebase_storage = firebase.storage()

cred = credentials.Certificate("CRED1.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'BUCKET'
})

credentials_gae = service_account.Credentials.from_service_account_file('CRED2.json')

data_store = datastore.Client(project="convertorstorage", credentials=credentials_gae)


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        mail = request.form['username']
        password = request.form['password']
        try:
            login = firebase_auth.sign_in_with_email_and_password(mail, password)
            session['user'] = login['idToken']
            return redirect('/storage')
        except Exception as e:
            print(e)
            return render_template('login.html', login_error="Email or password incorrect!")
    return render_template('login.html')


@app.route('/changePassword', methods=['POST', 'GET'])
def change_password():
    if request.method == 'POST':
        mail = request.form['username']
        try:
            firebase_auth.send_password_reset_email(mail)
            return render_template('change_password.html', change_password_message="An email was sent to reset password!")
        except Exception as e:
            print(e)
            return render_template('change_password.html', change_password_error='Email incorrect!')
    return render_template('change_password.html')


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        mail = request.form['username']
        password = request.form['password']
        confirm_password = request.form['passwordConfirm']
        print(mail, password, confirm_password)
        if len(password) < 6:
            return render_template('register.html', short_password_error="Password should be at least 6 characters!")
        if password == confirm_password:
            try:
                user = firebase_auth.create_user_with_email_and_password(mail, password)
                firebase_auth.send_email_verification(user['idToken'])
                return redirect("/")
            except Exception as e:
                print(e)
                return render_template('register.html', used_data_error="Credentials already in use!")
        else:
            return render_template('register.html', passwords_error="Passwords don't match!")
    return render_template('register.html')


@app.route('/storage', methods=['POST', 'GET'])
def store_search():
    if 'user' not in session:
        return redirect('/')
    user = firebase_auth.get_account_info(session['user'])
    my_files = get_files()
    if request.method == 'POST':
        if request.files:
            file_to_upload = request.files["file"]
            try:
                extension = os.path.splitext(file_to_upload.filename)[1]
                name = os.path.splitext(file_to_upload.filename)[0]
                if extension not in ['.txt', '.mp3']:
                    return render_template('file_storage.html', len=len(my_files), names=my_files,
                                           upload_error="You have to choose a txt or mp3 file!",
                                           user_email=user['users'][0]['email'])
                if name in my_files:
                    return render_template('file_storage.html', len=len(my_files), names=my_files,
                                           upload_error="You have already a file with this name!",
                                           user_email=user['users'][0]['email'])
                uid = user['users'][0]['localId']
                new_file_path = 'user/' + uid + '/textFiles/' + file_to_upload.filename
                file_url = firebase_storage.child(new_file_path).put(file_to_upload, session['user'])
                entity1 = datastore.Entity(key=data_store.key('file-token'))
                entity1.update({"file_name": new_file_path, "access_token": file_url['downloadTokens']})
                data_store.put(entity1)

                extension = os.path.splitext(file_to_upload.filename)
                if extension[1] == '.mp3':
                    translation = record_sound(new_file_path)
                    new_file_path = 'user/' + uid + '/textFiles/' + extension[0] + ".txt"
                    file_url = firebase_storage.child(new_file_path).put(translation.encode('utf-8'), session['user'])
                    entity2 = datastore.Entity(key=data_store.key('file-token'))
                    entity2.update({"file_name": new_file_path, "access_token": file_url['downloadTokens']})
                    data_store.put(entity2)
                else:
                    query = data_store.query(kind="file-token")
                    query.add_filter("file_name", "=", new_file_path)
                    token = ""
                    for result in query.fetch(limit=1):
                        token = result['access_token']
                    print(token)
                    url = firebase_storage.child(new_file_path).get_url(token)
                    response = req.urlopen(url).read()
                    text = response.decode("UTF-8")

                    translation = create_voice_file(text)
                    new_file_path = 'user/' + uid + '/textFiles/' + extension[0] + ".mp3"
                    file_url = firebase_storage.child(new_file_path).put(translation, session['user'])
                    entity2 = datastore.Entity(key=data_store.key('file-token'))
                    entity2.update({"file_name": new_file_path, "access_token": file_url['downloadTokens']})
                    data_store.put(entity2)
                return redirect(request.url)
            except Exception as e:
                print(e)
                delete_file(file_to_upload.filename)
                return render_template('file_storage.html', len=len(my_files), names=my_files,
                                       upload_error="The file is too big.",
                                       user_email=user['users'][0]['email'])

    return render_template('file_storage.html', user_email=user['users'][0]['email'], len=len(my_files), names=my_files)


def get_files():
    result = []
    user = firebase_auth.get_account_info(session['user'])
    bucket = storage.bucket()
    blobs = bucket.list_blobs()
    for blob in blobs:
        uid = user['users'][0]['localId']
        if uid in blob.name:
            components = blob.name.split("/")
            file_name = components[len(components) - 1].split(".")[0]
            if file_name not in result:
                result.append(file_name)
    return result


def record_sound(file_audio):
    client = speech_v1p1beta1.SpeechClient(credentials=credentials_gae)

    storage_uri = "BUCKET_URI" + file_audio
    sample_rate_hertz = 44100
    language_code = "en-US"

    encoding = enums.RecognitionConfig.AudioEncoding.MP3
    config = {
        "sample_rate_hertz": sample_rate_hertz,
        "language_code": language_code,
        "encoding": encoding
    }
    audio = {"uri": storage_uri}

    operation = client.long_running_recognize(config, audio)
    response = operation.result()
    translation = ''
    for result in response.results:
        alternative = result.alternatives[0]
        translation += alternative.transcript
    return translation


def create_voice_file(text):

    client = texttospeech.TextToSpeechClient(credentials=credentials_gae)

    input_text = types.cloud_tts_pb2.SynthesisInput(text=text)

    voice = types.cloud_tts_pb2.VoiceSelectionParams(
        language_code='en-US',
        name='en-US-Standard-C',
        ssml_gender=texttospeech.enums.SsmlVoiceGender.NEUTRAL)

    audio_config = texttospeech.types.cloud_tts_pb2.AudioConfig(
        audio_encoding=texttospeech.enums.AudioEncoding.MP3)

    response = client.synthesize_speech(input_text, voice, audio_config)
    return response.audio_content


@app.route('/storage/actionFile', methods=['POST'])
def file_action():
    name = request.form['submitButton'].split("-")[1]
    user = firebase_auth.get_account_info(session['user'])
    if request.form['submitButton'].startswith('deleteFile'):
        delete_file(name)
    else:
        try:
            uid = user['users'][0]['localId']
            file_name = 'user/' + uid + '/textFiles/' + name
            query = data_store.query(kind="file-token")
            query.add_filter("file_name", "=", file_name)
            token = ""
            for result in query.fetch(limit=1):
                token = result['access_token']
            url = firebase_storage.child(file_name).get_url(token)
            response = req.urlopen(url).read()
            return send_file(io.BytesIO(response), as_attachment=True, attachment_filename=name)
        except Exception as e:
            print(e)
            return redirect("/storage")

    return redirect("/storage")


def delete_file(name):
    try:
        user = firebase_auth.get_account_info(session['user'])
        uid = user['users'][0]['localId']
        file_name = 'user/' + uid + '/textFiles/' + name
        bucket = storage.bucket()
        bucket.blob(file_name).delete()
        query = data_store.query(kind="file-token")
        query.add_filter("file_name", "=", file_name)
        for result in query.fetch(limit=1):
            data_store.delete(result.key)
        time.sleep(2)
    except Exception as e:
        print(e)


@app.route('/logout', methods=['POST', 'GET'])
def logout():
    try:
        firebase_auth.current_user = None
        del session['user']
    except Exception as e:
        print(e)
    return redirect("/")


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8090, debug=True)
