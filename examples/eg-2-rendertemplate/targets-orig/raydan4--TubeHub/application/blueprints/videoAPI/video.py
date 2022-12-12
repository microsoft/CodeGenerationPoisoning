from flask import Blueprint, render_template, abort, request, redirect, flash, session, url_for
from jinja2 import TemplateNotFound
import os.path
from os import remove
from requests import get
from hashlib import sha3_256
import pymysql.cursors

video = Blueprint('video', __name__, template_folder='templates', static_folder='static')

VIDEO_DIR = '/usr/src/app/blueprints/videoAPI/static/videos/'
WATCH_DIR = 'static/videos/'

def connect_to_db():
    return pymysql.connect(host='maria',
                            user='root',
                            password='changeme',
                            db='tubehub',
                            charset='utf8mb4',
                            cursorclass=pymysql.cursors.DictCursor)
 

@video.route('/', methods=['GET'])
def show_videos():
    try:
        return render_template('/videos.html')
    except TemplateNotFound:
        abort(404)


@video.route('/upload', methods=['GET', 'POST'])
def show_upload():
    if request.method == 'POST':
        # Get parameters from request
        title = request.form.get('title')
        description = request.form.get('description')
        
        # Validate form input
        # Logged in
        if not session.get('logged_in'):
            abort(401)
        username = session.get('username')
        # Video is Present
        video = request.files.get('video')
        if video:
            filehash = sha3_256(video.read()).hexdigest()
            filetype = video.content_type
            # Save video file to server (no validation lol all in same directory)
            video.save(os.path.join(VIDEO_DIR, filehash))
        else:
            # Get file from link
            link = request.form.get('link')
            if not link:
                abort(400, description='No video file')
            video = get(link)
            filehash = sha3_256(video.content).hexdigest()
            filetype = video.headers.get('Content-Type')
            with open(os.path.join(VIDEO_DIR, filehash), 'wb+') as f:
                f.write(video.content)

        
        # Connect to database
        connection = connect_to_db()

        # Add video info to database
        try:
            with connection.cursor() as cur:
                sql = "INSERT INTO `video` (`title`, `username`, `description`, `hash`, `filetype`) VALUES (%s, %s, %s, %s, %s)"
                cur.execute(sql, (title, username, description, filehash, filetype))
                connection.commit()
        except:
            abort(404)
        finally:
            connection.close()
        return redirect(f'/video/watch?hash={filehash}')

    if request.method == 'GET':
        try:
            return render_template('/video/upload.html')
        except TemplateNotFound:
            abort(404)

@video.route('/delete', methods=['GET', 'POST'])
def show_delete():
    # Check logged in
    if not session.get('logged_in'):
        abort(403)
    if request.method == 'GET':
        filename = request.args.get('hash')
    elif request.method == 'POST':
        filehash = request.form.get('hash')
       
    # Remove database entry
    connection = connect_to_db()
    try:
        with connection.cursor() as cur:
            sql = f'DELETE FROM `video` WHERE `hash` = "{filehash}" AND `username` = "{session.get("username")}";'
            cur.execute(sql)
            connection.commit()
        
        # Remove file from disk
        os.remove(os.path.join(VIDEO_DIR, filehash))
    except Exception as e:
        abort(400, description=e)
    finally:
        connection.close()
    return redirect('/')

@video.route('/watch')
def show_watch():
    try:
        # Source from db
        filehash = request.args.get('hash')
        if not filehash:
            abort(400)
        source = os.path.join(WATCH_DIR, filehash)

        # Get other fields from database
        connection = connect_to_db()
        try:
            with connection.cursor() as cur:
                sql = f'SELECT `title`, `username`, `filetype`,`description` FROM `video` WHERE `hash` = "{filehash}";'
                cur.execute(sql)
                result = cur.fetchone()
                title = result.get('title')
                username = result.get('username')
                filetype = result.get('filetype')
                description = result.get('description')
        except:
            abort(404)
        finally:
            connection.close()
        return render_template('/video/watch.html', title=title, source=source, username=username, filetype=filetype, description=description)
    except TemplateNotFound:
        abort(404)

