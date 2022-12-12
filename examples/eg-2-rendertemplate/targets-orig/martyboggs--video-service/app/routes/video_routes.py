import boto3
import os
import json
from flask import render_template, request, redirect, url_for, Blueprint

S3_BUCKET = os.environ.get('S3_BUCKET')
ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY_ID')
SECRET_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
s3 = boto3.client('s3',
  aws_access_key_id=ACCESS_KEY,
  aws_secret_access_key=SECRET_KEY
)

video_api = Blueprint('video_api', __name__)

@video_api.route('/save', methods=['POST'])
def save_video():
  return 'yes'


# https://devcenter.heroku.com/articles/s3-upload-python
@video_api.route('/account')
def account():
  return render_template('account.html')


@video_api.route('/sign_s3')
def sign_s3():
  file_name = request.args.get('file_name')
  file_type = request.args.get('file_type')

  presigned_post = s3.generate_presigned_post(
    Bucket=S3_BUCKET,
    Key=file_name,
    Fields={'acl': 'public-read', 'Content-Type': file_type},
    Conditions=[
      {'acl': 'public-read'},
      {'Content-Type': file_type}
    ],
    ExpiresIn=3600
  )

  return json.dumps({
    'data': presigned_post,
    'url': 'https://%s.s3.amazonaws.com/%s' % (S3_BUCKET, file_name)
  })


@video_api.route('/submit_form', methods=['POST'])
def submit_form():
  username = request.form['username']
  full_name = request.form['full-name']
  avatar_url = request.form['avatar-url']

  update_account(username, full_name, avatar_url)

  return redirect(url_for('profile'))


def update_account(username, full_name, avatar_url):
  return
