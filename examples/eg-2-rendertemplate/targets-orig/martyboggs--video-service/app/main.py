import sys
import os
import boto3
from flask import Flask, render_template
from routes.video_routes import video_api
from routes.test_routes import test_api
# pylint: disable=E1101

S3_BUCKET = os.environ.get('S3_BUCKET')
ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY_ID')
SECRET_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
s3 = boto3.resource('s3',
  aws_access_key_id=ACCESS_KEY,
  aws_secret_access_key=SECRET_KEY
)

app = Flask(__name__)

app.register_blueprint(video_api, url_prefix='/video')
app.register_blueprint(test_api, url_prefix='/test')

@app.route('/')
def index():
  bucket = s3.Bucket(S3_BUCKET)
  files = bucket.objects.all()
  return render_template('index.html', data=files)

@app.route('/upload')
def hello_world():
  return render_template('upload.html')

@app.route("/hello")
def hello():
  version = "{}.{}".format(sys.version_info.major, sys.version_info.minor)
  message = "Hello World from Flask in a uWSGI Nginx Docker container with Python {} (default)".format(
    version
  )
  return message

if __name__ == "__main__":
  app.run(host="0.0.0.0", debug=True, port=80)



