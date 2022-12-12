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

with open("", "r") as f:
    content = f.read()
firebaseConfig = json.loads(content)
firebase = pyrebase.initialize_app(firebaseConfig)
firebase_auth = firebase.auth()
firebase_storage = firebase.storage()

cred = credentials.Certificate("")
firebase_admin.initialize_app(cred, {
    'storageBucket': ''
})

credentials_gae = service_account.Credentials.from_service_account_file('')

data_store = datastore.Client(project="convertorstorage", credentials=credentials_gae)


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        mail = request.form['username']
        password = request.form['password']
        try:
            login = firebase_auth.sign_in_with_email_and_password(mail, password)
            query = data_store.query(kind="users")
            query.add_filter("user_token", "=", login['localId'])
            user_type = ""
            inst = ""
            for result in query.fetch(limit=1):
                user_type = result['type']
                inst = result['institution_name']
            session['user'] = login['idToken']
            session['user_type'] = user_type
            session['user_inst'] = inst
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
        validation_code = request.form['validationCode']
        print(mail, password, confirm_password, validation_code)
        if len(password) < 6:
            return render_template('register.html', short_password_error="Password should be at least 6 characters!")
        if password == confirm_password:
            query = data_store.query(kind="accounts_to_be_created")
            query.add_filter("validation_code", "=", validation_code)
            institution = ""
            for result in query.fetch(limit=1):
                institution = result['institution_name']
                data_store.delete(result.key)
            print(institution)
            if institution != "":
                try:
                    user = firebase_auth.create_user_with_email_and_password(mail, password)
                    firebase_auth.send_email_verification(user['idToken'])
                    entity = datastore.Entity(key=data_store.key('users'))
                    entity.update({"user_token": user['localId'], "type": "admin", "institution_name": institution})
                    data_store.put(entity)
                    return redirect("/")
                except Exception as e:
                    print(e)
                    return render_template('register.html', used_data_error="Credentials already in use!")
            else:
                return render_template('register.html', code_error="Code invalid!")
        else:
            return render_template('register.html', passwords_error="Passwords don't match!")
    return render_template('register.html')


@app.route('/storage', methods=['POST', 'GET'])
def store_search():
    if 'user' not in session:
        return redirect('/')
    user_type = session['user_type']
    user = firebase_auth.get_account_info(session['user'])
    if user_type == "admin":
        return create_accounts_as_admin(request, user)
    elif user_type == "teacher":
        return teacher_storage(request, user)
    else:
        return student_storage(request, user)


def get_teacher_options(uid):
    query = data_store.query(kind="teacher-subject-relation")
    query.add_filter("user_token", "=", uid)
    subject_id = []
    for result in query.fetch():
        subject_id.append(result['subject_id'])

    subjects = []
    students = []
    for sub_id in subject_id:
        query = data_store.query(kind="subject")
        key = data_store.key('subject', sub_id)
        query.key_filter(key, '=')
        for result in query.fetch():
            subjects.append(result['name'])

        query = data_store.query(kind="student-subject-relation")
        query.add_filter("subject_id", "=", sub_id)
        for result in query.fetch():
            students.append(result['user_token'])

    groups = {"All"}
    for student in students:
        query = data_store.query(kind="students")
        query.add_filter("user_token", "=", student)
        for result in query.fetch():
            groups.add(result["group"])
    return subjects, groups


def get_student_options(uid):
    query = data_store.query(kind="student-subject-relation")
    query.add_filter("user_token", "=", uid)
    subject_id = []
    for result in query.fetch():
        subject_id.append(result['subject_id'])
    subjects = []
    teachers_tokens = {"all_teachers"}
    for sub_id in subject_id:
        query = data_store.query(kind="subject")
        key = data_store.key('subject', sub_id)
        query.key_filter(key, '=')
        for result in query.fetch():
            subjects.append(result['name'])

        query = data_store.query(kind="teacher-subject-relation")
        query.add_filter("subject_id", "=", sub_id)
        for result in query.fetch():
            teachers_tokens.add(result['user_token'])

    teachers = {"All"}
    for teacher in teachers_tokens:
        query = data_store.query(kind="teachers")
        query.add_filter("user_token", "=", teacher)
        for result in query.fetch():
            teachers.add(result["name"])
    return subjects, teachers, teachers_tokens


def create_accounts_as_admin(request, user):
    uid = user['users'][0]['localId']
    subjects, ids = get_subjects(uid)
    account_names, account_uids = get_all_created_accounts(uid)
    if request.method == 'POST':
        email = request.form['email']
        firstName = request.form['first_name']
        lastName = request.form['last_name']
        acc_type = request.form['type']
        selected_subjects = request.form.getlist("subject")
        group = request.form['group']
        if email == "" or firstName == "" or lastName == "" or acc_type == "" or selected_subjects == []:
            return render_template('admin_register.html', null_data_error="All fields are mandatory!",
                                   user_email=user['users'][0]['email'], len_subjects=len(subjects), subjects=subjects,
                                   len=len(account_names), names=account_names, uids=account_uids)
        elif acc_type == "student" and group == "":
            return render_template('admin_register.html', null_data_error="All fields are mandatory!",
                                   user_email=user['users'][0]['email'], len_subjects=len(subjects), subjects=subjects,
                                   len=len(account_names), names=account_names, uids=account_uids)
        try:
            new_acc = firebase_auth.create_user_with_email_and_password(email, firstName[:3] + lastName[:3] + "2020")
            firebase_auth.send_email_verification(new_acc['idToken'])
        except Exception as e:
            print(e)
            return render_template('admin_register.html', used_data_error="Email already in use!",
                                   user_email=user['users'][0]['email'], len_subjects=len(subjects), subjects=subjects,
                                   len=len(account_names), names=account_names, uids=account_uids)

        if acc_type == 'student':
            student_entity = datastore.Entity(key=data_store.key('students'))
            student_entity.update(
                {"user_token": new_acc['localId'], "name": firstName + " " + lastName, "group": group})
            data_store.put(student_entity)

            for subject in selected_subjects:
                student_subject_entity = datastore.Entity(key=data_store.key('student-subject-relation'))
                student_subject_entity.update(
                    {"user_token": new_acc['localId'], "subject_id": ids[subjects.index(subject)]})
                data_store.put(student_subject_entity)
        else:
            teacher_entity = datastore.Entity(key=data_store.key('teachers'))
            teacher_entity.update({"user_token": new_acc['localId'], "name": firstName + " " + lastName})
            data_store.put(teacher_entity)
            for subject in selected_subjects:
                teacher_subject_entity = datastore.Entity(key=data_store.key('teacher-subject-relation'))
                teacher_subject_entity.update(
                    {"user_token": new_acc['localId'], "subject_id": ids[subjects.index(subject)]})
                data_store.put(teacher_subject_entity)

        user_entity = datastore.Entity(key=data_store.key('users'))
        user_entity.update(
            {"user_token": new_acc['localId'], "type": acc_type, "institution_name": session['user_inst']})
        data_store.put(user_entity)
        return redirect(request.url)

    return render_template('admin_register.html', user_email=user['users'][0]['email'],
                           len_subjects=len(subjects), subjects=subjects, len=len(account_names),
                           names=account_names, uids=account_uids)


def get_all_created_accounts(admin_uid):
    names = []
    uids = []
    query = data_store.query(kind="users")
    query.add_filter("institution_name", "=", session['user_inst'])
    for result in query.fetch():
        user_uid = result['user_token']
        if user_uid != admin_uid:
            uids.append(user_uid)
        if result['type'] == 'student':
            query2 = data_store.query(kind="students")
            query2.add_filter("user_token", "=", user_uid)
            for student_result in query2.fetch(limit=1):
                names.append('Student: ' + student_result['name'])
        if result['type'] == 'teacher':
            query2 = data_store.query(kind="teachers")
            query2.add_filter("user_token", "=", user_uid)
            for teacher_result in query2.fetch(limit=1):
                names.append('Teacher: ' + teacher_result['name'])
    return names, uids


def teacher_storage(request, user):
    my_files, real_files = get_files()
    uid = user['users'][0]['localId']
    students_files, students_real_files = get_files_from_students(uid)
    subjects, groups = get_teacher_options(uid)
    groups = list(groups)
    if request.method == 'POST':
        file_to_upload = request.files["file"]
        try:
            extension = os.path.splitext(file_to_upload.filename)[1]
            name = os.path.splitext(file_to_upload.filename)[0]
            if extension not in ['.txt', '.mp3']:
                return render_template('teacher_storage.html', len=len(my_files), names=my_files, file_names=real_files,
                                       upload_error="You have to choose a txt or mp3 file!",
                                       user_email=user['users'][0]['email'],
                                       len_subjects=len(subjects), subjects=subjects, len_groups=len(groups),
                                       groups=groups, len2=len(students_files), names2=students_files, file_names2=students_real_files)
            if name in my_files:
                return render_template('teacher_storage.html', len=len(my_files), names=my_files, file_names=real_files,
                                       upload_error="You have already a file with this name!",
                                       user_email=user['users'][0]['email'],
                                       len_subjects=len(subjects), subjects=subjects, len_groups=len(groups),
                                       groups=groups, len2=len(students_files), names2=students_files, file_names2=students_real_files)

            subject = request.form['subject']
            group = request.form['group']
            new_file_path = session['user_inst'] + "/" + subject + "/" + group + "/" + file_to_upload.filename
            print(new_file_path)
            file_url = firebase_storage.child(new_file_path).put(file_to_upload, session['user'])
            entity1 = datastore.Entity(key=data_store.key('file-token'))
            entity1.update({"file_name": new_file_path, "access_token": file_url['downloadTokens'], "owner": uid})
            data_store.put(entity1)

            extension = os.path.splitext(file_to_upload.filename)
            if extension[1] == '.mp3':
                translation = record_sound(new_file_path)
                new_file_path = session['user_inst'] + "/" + subject + '/' + group + "/" + extension[0] + ".txt"
                file_url = firebase_storage.child(new_file_path).put(translation.encode('utf-8'), session['user'])
                entity2 = datastore.Entity(key=data_store.key('file-token'))
                entity2.update({"file_name": new_file_path, "access_token": file_url['downloadTokens'], "owner": uid})
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
                new_file_path = session['user_inst'] + "/" + subject + '/' + group + "/" + extension[0] + ".mp3"
                file_url = firebase_storage.child(new_file_path).put(translation, session['user'])
                entity2 = datastore.Entity(key=data_store.key('file-token'))
                entity2.update({"file_name": new_file_path, "access_token": file_url['downloadTokens'], "owner": uid})
                data_store.put(entity2)
            return redirect(request.url)
        except Exception as e:
            print(e)
            delete_file(new_file_path)
            return render_template('teacher_storage.html', len=len(my_files), names=my_files, file_names=real_files,
                                   upload_error="The file is too big.",
                                   user_email=user['users'][0]['email'],
                                   len_subjects=len(subjects), subjects=subjects, len_groups=len(groups), groups=groups,
                                   len2=len(students_files), names2=students_files, file_names2=students_real_files)

    return render_template("teacher_storage.html", user_email=user['users'][0]['email'], len=len(my_files), file_names=real_files,
                           names=my_files,
                           len_subjects=len(subjects), subjects=subjects, len_groups=len(groups), groups=groups,
                           len2=len(students_files), names2=students_files, file_names2=students_real_files)


def student_storage(request, user):
    my_files, real_files = get_files()
    uid = user['users'][0]['localId']
    teacher_files, teacher_real_files = get_files_from_teacher(uid)
    subjects, teachers, teachers_tokens = get_student_options(uid)
    teachers = list(teachers)
    teachers_tokens = list(teachers_tokens)
    if request.method == 'POST':
        if request.files:
            file_to_upload = request.files["file"]
            try:
                extension = os.path.splitext(file_to_upload.filename)[1]
                name = os.path.splitext(file_to_upload.filename)[0]
                if extension not in ['.txt', '.mp3']:
                    return render_template('student_storage.html', len=len(my_files), names=my_files,
                                           file_names=real_files,
                                           upload_error="You have to choose a txt or mp3 file!",
                                           user_email=user['users'][0]['email'],
                                           len_subjects=len(subjects), subjects=subjects,
                                           len_teachers=len(teachers), teachers=teachers,
                                           len2=len(teacher_files), names2=teacher_files,
                                           file_names2=teacher_real_files)
                if name in my_files:
                    return render_template('student_storage.html', len=len(my_files), names=my_files,
                                           file_names=real_files,
                                           upload_error="You have already a file with this name!",
                                           user_email=user['users'][0]['email'],
                                           len_subjects=len(subjects), subjects=subjects,
                                           len_teachers=len(teachers), teachers=teachers,
                                           len2=len(teacher_files), names2=teacher_files,
                                           file_names2=teacher_real_files)
                uid = user['users'][0]['localId']
                subject = request.form['subject']
                teacher = request.form['teacher']
                teacher_uid = teachers_tokens[teachers.index(teacher)]
                if not check_subject_teacher_relation(teacher_uid, subject) and teacher != 'All':
                    return render_template('student_storage.html', len=len(my_files), names=my_files,
                                           file_names=real_files,
                                           upload_error="Wrong teacher - subject pair!",
                                           user_email=user['users'][0]['email'],
                                           len_subjects=len(subjects), subjects=subjects,
                                           len_teachers=len(teachers), teachers=teachers,
                                           len2=len(teacher_files), names2=teacher_files,
                                           file_names2=teacher_real_files)
                new_file_path = session['user_inst'] + "/" + subject + "/" + teacher_uid \
                                + "/" + file_to_upload.filename
                file_url = firebase_storage.child(new_file_path).put(file_to_upload, session['user'])
                entity1 = datastore.Entity(key=data_store.key('file-token'))
                entity1.update({"file_name": new_file_path, "access_token": file_url['downloadTokens'], "owner": uid})
                data_store.put(entity1)

                extension = os.path.splitext(file_to_upload.filename)
                if extension[1] == '.mp3':
                    translation = record_sound(new_file_path)
                    new_file_path = session['user_inst'] + "/" + subject + "/" + teachers_tokens[
                        teachers.index(teacher)] \
                                    + "/" + extension[0] + ".txt"
                    file_url = firebase_storage.child(new_file_path).put(translation.encode('utf-8'), session['user'])
                    entity2 = datastore.Entity(key=data_store.key('file-token'))
                    entity2.update(
                        {"file_name": new_file_path, "access_token": file_url['downloadTokens'], "owner": uid})
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
                    new_file_path = session['user_inst'] + "/" + subject + "/" + teachers_tokens[
                        teachers.index(teacher)] \
                                    + "/" + extension[0] + ".mp3"
                    file_url = firebase_storage.child(new_file_path).put(translation, session['user'])
                    entity2 = datastore.Entity(key=data_store.key('file-token'))
                    entity2.update(
                        {"file_name": new_file_path, "access_token": file_url['downloadTokens'], "owner": uid})
                    data_store.put(entity2)
                return redirect(request.url)
            except Exception as e:
                print(e)
                delete_file(file_to_upload.filename)
                return render_template('student_storage.html', len=len(my_files), names=my_files, file_names=real_files,
                                       upload_error="The file is too big.",
                                       user_email=user['users'][0]['email'],
                                       len_subjects=len(subjects), subjects=subjects, len_teachers=len(teachers),
                                       teachers=teachers, len2=len(teacher_files), names2=teacher_files,
                                       file_names2=teacher_real_files)

    return render_template('student_storage.html', user_email=user['users'][0]['email'], len=len(my_files),
                           names=my_files,
                           file_names=real_files,
                           len_subjects=len(subjects), subjects=subjects, len_teachers=len(teachers), teachers=teachers,
                           len2=len(teacher_files), names2=teacher_files, file_names2=teacher_real_files)


def check_subject_teacher_relation(teacher, subject):
    query = data_store.query(kind="subject")
    query.add_filter("name", "=", subject)
    query.add_filter("institution_name", "=", session['user_inst'])
    subject_id = ''
    for result in query.fetch(limit=1):
        subject_id = result.key.id
    query = data_store.query(kind="teacher-subject-relation")
    query.add_filter("subject_id", '=', subject_id)
    for result in query.fetch():
        if teacher == result['user_token']:
            return True
    return False


def get_subjects(uid):
    query = data_store.query(kind="users")
    query.add_filter("user_token", "=", uid)
    institution = ""
    for result in query.fetch(limit=1):
        institution = result['institution_name']

    query = data_store.query(kind="subject")
    query.add_filter("institution_name", "=", institution)
    subjects = []
    ids = []
    for result in query.fetch():
        subjects.append(result['name'])
        ids.append(result.key.id)
    return subjects, ids


def get_files():
    result = []
    user = firebase_auth.get_account_info(session['user'])

    uid = user['users'][0]['localId']
    query = data_store.query(kind="file-token")
    query.add_filter("owner", "=", uid)
    files = []
    real_files = []
    for result in query.fetch():
        components = result['file_name'].split("/")
        real_name = result['file_name'].split(".")[0]
        if real_name not in real_files:
            real_files.append(real_name)
        if session['user_type'] == 'teacher':
            file_name = components[1] + " - " + components[2] + " - " + components[len(components) - 1].split(".")[0]
        else:
            query = data_store.query(kind="teachers")
            query.add_filter("user_token", "=", components[2])
            name = ""
            for result in query.fetch(limit=1):
                name = result['name']
            file_name = components[1] + " - " + name + " - " + components[len(components) - 1].split(".")[0]
        if file_name not in files:
            files.append(file_name)
    return files, real_files


def get_files_from_teacher(uid):
    subjects, teachers, teachers_tokens = get_student_options(uid)
    teachers = list(teachers)
    teachers_tokens = list(teachers_tokens)
    result_files = []
    query = data_store.query(kind="students")
    query.add_filter("user_token", "=", uid)
    group = ""
    for result in query.fetch(limit=1):
        group = result['group']
    bucket = storage.bucket()
    blobs = bucket.list_blobs()
    files = []
    real_files = []
    for blob in blobs:
        files.append(blob.name)

    for subject in subjects:
        path1 = session['user_inst'] + "/" + subject + "/" + group
        path2 = session['user_inst'] + "/" + subject + "/" + "All"
        for file in files:
            if file.startswith(path1) or file.startswith(path2):
                query = data_store.query(kind="file-token")
                query.add_filter("file_name", "=", file)
                token = ""
                for result in query.fetch(limit=1):
                    token = result['owner']
                components = file.split("/")
                real_name = file.split(".")[0]
                if real_name not in real_files:
                    real_files.append(real_name)
                teacher_name = teachers[teachers_tokens.index(token)]
                name = components[len(components) - 1].split(".")[0]
                file_name = teacher_name + " - " + components[1] + " - " + name
                if file_name not in result_files:
                    result_files.append(file_name)
    print(result_files)
    return result_files, real_files


def get_files_from_students(uid):
    subjects, _ = get_teacher_options(uid)
    result_files = []

    bucket = storage.bucket()
    blobs = bucket.list_blobs()
    files = []
    real_files = []
    for blob in blobs:
        files.append(blob.name)

    for subject in subjects:
        path1 = session['user_inst'] + "/" + subject + "/" + uid
        path2 = session['user_inst'] + "/" + subject + "/" + "all_teachers"
        for file in files:
            if file.startswith(path1) or file.startswith(path2):
                query = data_store.query(kind="file-token")
                query.add_filter("file_name", "=", file)
                token = ""
                for result in query.fetch(limit=1):
                    token = result['owner']

                query = data_store.query(kind="students")
                query.add_filter("user_token", "=", token)
                student_name = ""
                for result in query.fetch(limit=1):
                    student_name = result['name']

                components = file.split("/")
                real_name = file.split(".")[0]
                if real_name not in real_files:
                    real_files.append(real_name)
                name = components[len(components) - 1].split(".")[0]
                file_name = student_name + " - " + components[1] + " - " + name
                if file_name not in result_files:
                    result_files.append(file_name)
    print(result_files)
    return result_files, real_files


def record_sound(file_audio):
    client = speech_v1p1beta1.SpeechClient(credentials=credentials_gae)

    storage_uri = "" + file_audio
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
    name = request.form['submitButton'].split("+")[1]
    components = name.split("/")
    file_name = components[len(components) - 1]
    user = firebase_auth.get_account_info(session['user'])
    if request.form['submitButton'].startswith('deleteFile'):
        delete_file(name)
    else:
        try:
            query = data_store.query(kind="file-token")
            query.add_filter("file_name", "=", name)
            token = ""
            for result in query.fetch(limit=1):
                token = result['access_token']
            url = firebase_storage.child(name).get_url(token)
            response = req.urlopen(url).read()
            return send_file(io.BytesIO(response), as_attachment=True, attachment_filename=file_name)
        except Exception as e:
            print(e)
            return redirect("/storage")

    return redirect("/storage")


def delete_file(name):
    try:
        bucket = storage.bucket()
        bucket.blob(name).delete()
        query = data_store.query(kind="file-token")
        query.add_filter("file_name", "=", name)
        for result in query.fetch(limit=1):
            data_store.delete(result.key)
        time.sleep(2)
    except Exception as e:
        print(e)


@app.route('/storage/deleteAccount', methods=['POST'])
def delete_account():
    uid = request.form['submitButton']
    query = data_store.query(kind="users")
    query.add_filter("user_token", "=", uid)
    for result in query.fetch(limit=1):
        if result['type'] == 'student':
            acc_type = 'student'
        else:
            acc_type = 'teacher'
        data_store.delete(result.key)
    if acc_type == 'student':
        query = data_store.query(kind="students")
        query.add_filter("user_token", "=", uid)
        for result in query.fetch(limit=1):
            data_store.delete(result.key)
        query = data_store.query(kind="student-subject-relation")
        query.add_filter("user_token", "=", uid)
        for result in query.fetch():
            data_store.delete(result.key)
    else:
        query = data_store.query(kind="teachers")
        query.add_filter("user_token", "=", uid)
        for result in query.fetch(limit=1):
            data_store.delete(result.key)
        query = data_store.query(kind="teacher-subject-relation")
        query.add_filter("user_token", "=", uid)
        for result in query.fetch():
            data_store.delete(result.key)
    query = data_store.query(kind='file-token')
    query.add_filter("owner", "=", uid)
    bucket = storage.bucket()
    for result in query.fetch():
        bucket.blob(result['file_name']).delete()
        data_store.delete(result.key)
    auth.delete_user(uid)
    return redirect('/storage')


@app.route('/logout', methods=['POST', 'GET'])
def logout():
    try:
        firebase_auth.current_user = None
        del session['user']
        del session['user_type']
        del session['user_inst']
    except Exception as e:
        print(e)
    return redirect("/")


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8090, debug=True)
