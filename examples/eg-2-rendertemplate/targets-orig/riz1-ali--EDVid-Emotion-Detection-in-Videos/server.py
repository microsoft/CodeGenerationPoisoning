import glob
import json
import logging
import os
import time
import urllib.request
from functools import wraps
from os import environ as env
import plotly
import plotly.graph_objs as go


import cv2
import dlib
import face_recognition
import numpy as np
from authlib.integrations.flask_client import OAuth
from celery import Celery, group
from dotenv import find_dotenv, load_dotenv
from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   session, url_for)
from flask_sqlalchemy import SQLAlchemy
from imutils import face_utils
from six.moves.urllib.parse import urlencode
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename

import constants
from notebooks.preprocess import preprocess_input
from notebooks.utils import *
import ray
ray.init(num_cpus=4, ignore_reinit_error=True)

logging.basicConfig(level=logging.DEBUG)

try:
    ENV_FILE = find_dotenv()
    if ENV_FILE:
        load_dotenv(ENV_FILE)
except IOError:
    print("Error in opening the ENV file")

AUTH0_CALLBACK_URL = env.get(constants.AUTH0_CALLBACK_URL)
AUTH0_CLIENT_ID = env.get(constants.AUTH0_CLIENT_ID)
AUTH0_CLIENT_SECRET = env.get(constants.AUTH0_CLIENT_SECRET)
AUTH0_DOMAIN = env.get(constants.AUTH0_DOMAIN)
AUTH0_BASE_URL = 'https://' + AUTH0_DOMAIN
AUTH0_AUDIENCE = env.get(constants.AUTH0_AUDIENCE)
UPLOAD_FOLDER = './public/'
ALLOWED_EXTENSIONS = set(['mp4'])


try:
    app = Flask(__name__, static_url_path='/public', static_folder='./public')
    app.secret_key = constants.SECRET_KEY
    app.debug = True
    app.config.from_object("config.Config")
except:
    print("Error in creating Flask application")

db = SQLAlchemy(app)

try:
    celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
except:
    print("Error in creating Celery application")

from models import User,Video
from tasks import create_user, create_vid, add_vid_path

try:
    oauth = OAuth(app)
    auth0 = oauth.register(
        'auth0',
        client_id=AUTH0_CLIENT_ID,
        client_secret=AUTH0_CLIENT_SECRET,
        api_base_url=AUTH0_BASE_URL,
        access_token_url=AUTH0_BASE_URL + '/oauth/token',
        authorize_url=AUTH0_BASE_URL + '/authorize',
        client_kwargs={
            'scope': 'openid profile email',
        },
    )
except:
    print("Error in creating OAuth application")

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if constants.PROFILE_KEY not in session:
            return redirect('/login')
        return f(*args, **kwargs)

    return decorated


# Controllers API
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/callback')
def callback_handling():
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()

    session[constants.JWT_PAYLOAD] = userinfo
    print(userinfo)
    session[constants.PROFILE_KEY] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }
    return redirect(url_for('dashboard'))


@app.route('/login')
def login():
    return auth0.authorize_redirect(redirect_uri=AUTH0_CALLBACK_URL, audience=AUTH0_AUDIENCE)


@app.route('/logout')
def logout():
    session.clear()
    params = {'returnTo': url_for('home', _external=True), 'client_id': AUTH0_CLIENT_ID}
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))

def get_emotion_list(ray_list):
    """
    Returns a Time Series Cumulative Count of Emotions and
    Count of Total Emotions 
    Parameters:
    	ray_list(list<list<string>>): List of Emotions Detected in Each Frame   
    Returns:
    	seq(dictionary: string->int): Count of Total Emotions
    	time_seq(dictionary: string->list): Time Series Cumulative Count of Emotions over all frames 
    """
    seq,time_seq = {},{}
    seq['angry']=0
    seq['disgust']=0
    seq['fear']=0
    seq['happy']=0
    seq['sad']=0
    seq['surprise']=0
    seq['neutral']=0
    time_seq['angry']=[]
    time_seq['disgust']=[]
    time_seq['fear']=[]
    time_seq['happy']=[]
    time_seq['sad']=[]
    time_seq['surprise']=[]
    time_seq['neutral']=[]
    for it in ray_list:
        for it1 in it[0]:
            if it1 == None:
                break
            seq[it1] += 1
        for it in time_seq.keys():
        	time_seq[it].append(seq[it])
    return seq,time_seq

def create_plot(ray_list, vid_path):
    tempData,time_data = get_emotion_list(ray_list)
    labelsList = []
    valuesList = []
    for i in sorted (tempData) :
        labelsList.append(i)
        valuesList.append(tempData[i])
    data = [
        go.Pie(
            labels=labelsList,
            values=valuesList,
            marker={
                'colors': ['#e16552','#447c69','#993767','#74c493','#3c8e9d','#e9d78e','#e4bf80']
            }
        )
    ]
    labels_2,time_seq = [],[]
    for i in sorted(time_data.keys()):
        labels_2.append(i)
        time_seq.append(time_data[i])
    color_seq = ['#e16552','#447c69','#993767','#74c493','#3c8e9d','#e9d78e','#e4bf80']
    data_2 = []
    for c in range(len(labels_2)):
        trace1 = {
          "line": {
            "color": color_seq[c], 
            "shape": "spline", 
            "width": 3
          }, 
          "mode": "lines", 
          "name": labels_2[c], 
          "type": "scatter", 
          "x": [i for i in range(len(time_seq[c]))],
          "y": time_seq[c]
        }
        data_2.append(trace1)

    graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)
    with open(vid_path + "_plot_1.json", "w") as outfile: 
        outfile.write(graphJSON)
    graphJSON = json.dumps(data_2, cls=plotly.utils.PlotlyJSONEncoder)
    with open(vid_path + "_plot_2.json", "w") as outfile: 
        outfile.write(graphJSON)

def generate_emotion_video(ray_list, vid_path, size):
    """
    Generates the video marked with emotions in frames and saves
    it in the database  
    Parameters:
    	ray_list (list<tuple(emotions,frame)>): A list of Tuple of Emotions Corresponding to 
    											the Frame
    	vid_path (string): Path the Final Video has to be stored
    	size (tuple(int,int)): Width and Height of Each Frame   
    Returns:
    	1: If Video Successfully Stored and Path written in Database
    	0: Otherwise
    """
    cap = cv2.VideoCapture(vid_path)
    logging.info(vid_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    vid_id = int(vid_path.split("/")[-1])
    try:
        out = cv2.VideoWriter(vid_path + '_emotion.webm',cv2.VideoWriter_fourcc(*'vp80'), fps, size)
    except:
        print("Error in creating an output file")
    try:
        ray_list = ray.get(ray_list)
    except:
        print("Error in getting emotion distribution for the uploaded video")
    try:
        create_plot(ray_list, vid_path)
    except:
        print("Error in generating a Pie Chart plot")

    try:
        for iterx in ray_list:
            out.write(iterx[1])
        out.release()
        logging.info(vid_path[len(UPLOAD_FOLDER) + 1:])
        video = Video.query.filter_by(id=vid_id).first()
        video.processed = True
        db.session.commit()
        return 1
    except:
        print("Error in generating the output video")
        return 0  

@ray.remote
class Model(object):
	def __init__(self):
		"""
		Contructor for Class Model
		"""
		from keras.models import load_model
		emotion_model_path = './notebooks/model.hdf5'
		self.labels = {
			0:'angry',
			1:'disgust',
			2:'fear',
			3:'happy',
			4:'sad',
			5:'surprise',
			6:'neutral'
		}
		self.frame_window = 10
		self.emotion_offsets = (20, 40)
		self.detector = dlib.get_frontal_face_detector()
		self.emotion_classifier = load_model(emotion_model_path)
	

	def predictFace(self, gray_image, face):
		"""
		Predict Emotion for the Given Face in the Frame

		Parameters:
			gray_image (2D int list): Comtains the Black and White Representation
									  for the given frame
			face (object<rectangle>): Arguments of Face Detected using dlib.get_frontal_face_detector()

		Returns:
			emotion_text (string): Emotion Detected for the given face
		"""
		emotion_target_size = self.emotion_classifier.input_shape[1:3]

		x1, x2, y1, y2 = apply_offsets(face_utils.rect_to_bb(face), self.emotion_offsets)
		gray_face = gray_image[y1:y2, x1:x2]

		try:
			gray_face = cv2.resize(gray_face, (emotion_target_size))
		except:
			return None
		gray_face = preprocess_input(gray_face, True)
		gray_face = np.expand_dims(gray_face, 0)
		gray_face = np.expand_dims(gray_face, -1)
		emotion_prediction = self.emotion_classifier.predict(gray_face)
		emotion_probability = np.max(emotion_prediction)
		emotion_label_arg = np.argmax(emotion_prediction)
		emotion_text = self.labels[emotion_label_arg]
		return emotion_text

	def predictFrame(self, frame):
		"""
		Predict Emotion of Each Frame for the Given Frame

		Parameters:
			frame (3D int list): Contains the RGB representation for the Given Frame

		Returns:
			each_face_emotion (list<string>): List of Emotions detected
			tframe (3D int list): Frame marked with emotions for each frame in a
								  bounding box along with text 
		"""
		gray_image = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
		faces = self.detector(rgb_image)
		each_face_emotion = []
		for face in faces:
			each_face_emotion.append(self.predictFace(gray_image, face))

			if each_face_emotion[-1] == 'angry':
				color = np.asarray((255, 0, 0))
			elif each_face_emotion[-1] == 'sad':
				color = np.asarray((0, 0, 255))
			elif each_face_emotion[-1] == 'happy':
				color = np.asarray((255, 255, 0))
			elif each_face_emotion[-1] == 'surprise':
				color = np.asarray((0, 255, 255))
			elif each_face_emotion[-1] == 'disgust':
				color = np.asarray((0, 255, 0))				
			else:
				color = np.asarray((255, 255, 255))

			color = color.astype(int)
			color = color.tolist()

			name = each_face_emotion[-1]
			
			draw_bounding_box(face_utils.rect_to_bb(face), rgb_image, color)
			draw_text(face_utils.rect_to_bb(face), rgb_image, name,color, 0, -45, 0.5, 1)
		
		tframe = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
		return each_face_emotion,tframe

@ray.remote
def process_vid(vid_path):
    logging.info("Process Vid")
    logging.info(vid_path)
    try:
        cap = cv2.VideoCapture(vid_path)
    except:
        print("Error in VideoCapture")
    all_emotions = []
    detect = Model.remote()
    frames = []
    size = None
    while cap.isOpened():
        ret, frame = cap.read()
        if frame is None:
            break
        height, width, layers = frame.shape
        size = (width, height)

        
        all_emotions.append(detect.predictFrame.remote(frame))
    task = generate_emotion_video(all_emotions, vid_path, size)
    logging.info(task)
    return redirect('/allvideos')
    
celery.register_task(create_user)
celery.register_task(create_vid)
celery.register_task(add_vid_path)


def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def start_vid_processing(user_id, video_id):
    try:
        logging.info("In Start processing Function")
        vid_path = os.path.join(app.config["UPLOAD_FOLDER"], str(user_id), str(video_id))
        logging.info(vid_path)
        start = time.time()
        process_vid.remote(vid_path)
        end = time.time()
        logging.info(end - start)
    except:
        print("Error in sending asynchronous video processing request")

@app.route('/dashboard')
@requires_auth
def dashboard():
    try:
        user = User.query.filter_by(email=session[constants.JWT_PAYLOAD]['email']).first()
        logging.info(user)
    except:
        user = None
    if user is None:
        # task = create_user.apply(session[constants.JWT_PAYLOAD]['email'])
        task = create_user.apply(args=[session[constants.JWT_PAYLOAD]['email']])
        logging.info(task.task_id)
        try:
            user = User.query.filter_by(email=session[constants.JWT_PAYLOAD]['email']).first()
            os.mkdir(os.path.join(app.config['UPLOAD_FOLDER'], str(user.id)))
        except:
            user = None

    try:
        user = User.query.filter_by(email=session[constants.JWT_PAYLOAD]['email']).first() 
        logging.info(user)
    except:
        user = None
    try: 
        video_count = len(Video.query.filter_by(user_id=user.id).all())
    except:
        video_count = 0        
    return render_template('dashboard.html',
                           video_count=video_count,
                           userinfo=session[constants.JWT_PAYLOAD])

@app.route('/uploadsection')
@requires_auth
def uploadsection():
    try:
        user = User.query.filter_by(email=session[constants.JWT_PAYLOAD]['email']).first()
        logging.info(user)
    except:
        user = None
    if user is None:
        task = create_user.apply(args=[session[constants.JWT_PAYLOAD]['email']])
        logging.info(task.task_id)
        try:
            user = User.query.filter_by(email=session[constants.JWT_PAYLOAD]['email']).first()
            os.mkdir(os.path.join(app.config['UPLOAD_FOLDER'], str(user.id)))
        except:
            user = None
    try:
        user = User.query.filter_by(email=session[constants.JWT_PAYLOAD]['email']).first() 
        logging.info(user)
    except:
        user = None
    return render_template('upload.html',
                           userinfo=session[constants.JWT_PAYLOAD],
                           userinfo_pretty=json.dumps(session[constants.JWT_PAYLOAD], indent=4))

@app.route('/allvideos')
@requires_auth
def allvideos():
    try:
        user = User.query.filter_by(email=session[constants.JWT_PAYLOAD]['email']).first()
        logging.info(user)
    except:
        user = None
    if user is None:
        task = create_user.apply(args=[session[constants.JWT_PAYLOAD]['email']])
        logging.info(task.task_id)
        try:
            user = User.query.filter_by(email=session[constants.JWT_PAYLOAD]['email']).first()
            os.mkdir(os.path.join(app.config['UPLOAD_FOLDER'], str(user.id)))
        except:
            user = None
    try:
        user = User.query.filter_by(email=session[constants.JWT_PAYLOAD]['email']).first() 
        logging.info(user)
        video_list = Video.query.filter_by(user_id=user.id).all()
        video_list = video_list[::-1]
    except:
        user = None
    
    return render_template('allvideos.html',
                           videos = video_list,
                           userinfo=session[constants.JWT_PAYLOAD],
                           userinfo_pretty=json.dumps(session[constants.JWT_PAYLOAD], indent=4))

@app.route('/playvideo')
@requires_auth
def playvideo():
    video_path = request.args.get('video_path', None)
    video_name = request.args.get('video_name', None)
    try:
        with open(app.config["UPLOAD_FOLDER"] + "/" + video_path +"_plot_1.json", "r") as openfile: 
            plot_1 = json.load(openfile) 
        with open(app.config["UPLOAD_FOLDER"] + "/" + video_path +"_plot_2.json", "r") as openfile: 
            plot_2 = json.load(openfile) 
    except:
        print("Error in importing Pie Chart and Line visualisation")
    return render_template('playvideo.html',
                           video_path = video_path,
                           video_name = video_name,
                           plot1=plot_1,plot2=plot_2)

@app.route('/dashboard', methods=['POST'])
@requires_auth
def upload_file():
    if request.method == 'POST':
        try:
            user = User.query.filter_by(email=session[constants.JWT_PAYLOAD]['email']).first()
        except:
            user = None

        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No file selected for uploading')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            task = create_vid.apply(args=[user.id, filename])
            
            vid = Video.query.filter_by(user_id=user.id).all()[-1]
            # done = ray.get(task)

            task = add_vid_path.apply(args=[vid.id])

            vid = Video.query.filter_by(user_id=user.id).all()[-1]
            # done = ray.get(task)
            logging.info(vid.user_id)
            logging.info(vid.id)
            logging.info(vid.video_path)

            try:
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], str(user.id), str(vid.id)))
            except:
                print("Error in saving video")
            start_vid_processing(vid.user_id,vid.id)
            return redirect('/allvideos')
        else:
            flash('Allowed file type is mp4')
            return redirect('/uploadsection')

@app.route("/getVidStatus", methods=['GET'])
@requires_auth
def getVidStatus():
    try:
        user = User.query.filter_by(email=session[constants.JWT_PAYLOAD]['email']).first()
        vids = Video.query.filter_by(user_id=user.id).all()
        vids_json = {}
        for vid in vids:
            vids_json[vid.id] = {
                "id" : vid.id,
                "video_path" : vid.video_path,
                "video_title" : vid.video_title,
                "processed" : vid.processed
            }    
    except:
        user = None
    return jsonify(vids_json)

@app.errorhandler(HTTPException)
def handle_exception(e):
    return render_template('error.html',
                           error_code = e.code,
                           error_name = e.name,
                           error_description=e.description)