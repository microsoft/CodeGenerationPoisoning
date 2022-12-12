from flask import Flask, request, session, url_for, render_template, redirect, make_response, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from hashlib import sha256
from mysql import connector
from os import urandom, path, system, listdir, remove
from logging import warning
from urllib.parse import quote, unquote
from urllib.request import urlretrieve

#CHANGEME
ID = str(urandom(64))
UPLOAD_FOLDER = "/static/videos/"
ALLOWED_EXTENSIONS = {'mp4', 'webm', 'ogg', 'chaim'}

app = Flask(__name__, template_folder='templates')
app.secret_key = urandom(24)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#initialize database
db_connector = connector.connect(
    host="flask_db",
    user="root",
    password="absolutely_totally_secure",
    database="Application"
)
db_connector.reconnect(attempts=20, delay=5)


cursor = db_connector.cursor(buffered=True)

#
def get_file(filename):
    try:
        src = StaticPath + filename
        return open(src).read()
    except IOError as exc:
        return("No file file exists.")

@app.route("/", methods=['GET'])
def root():
    return render_template('index.html')

#
limiter = Limiter(app, key_func=get_remote_address)
@limiter.limit("1440/day;60/hour;10/minute")
@app.route("/login", methods=['POST'])
def login():
    username = request.values.get('username')
    password = request.values.get('password')
    query = "SELECT salt,password_hash_salt,Username FROM User_Login WHERE Username='%s';" % username
    cursor.execute(query)
    userdat = cursor.fetchall()

    if len(userdat) == 0:
        return render_template('index.html', error="Invalid Credentials: "+str(userdat))
    # hash
    hash = sha256((userdat[0][0] + password).encode()).hexdigest()

    if(userdat[0][1] == hash and username == userdat[0][2]):
        session["ID"] = ID
        session["Username"] = username
        response = make_response(redirect('landing'))
        response.set_cookie("ID", ID)
        return response
    elif len(userdat) > 1:
        return render_template('index.html', error="Invalid Credentials: "+str(userdat))
    else:
        return render_template('index.html', error="Invalid Credentials")

#
@app.route("/landing", methods=['GET'])
def landing():
    if request.cookies.get("ID") == ID and "ID" in session:
        videos = []

        for video in listdir(UPLOAD_FOLDER):
            query = "SELECT * FROM Video_files WHERE Path_To_Video=(%s)"  
            data = cursor.execute(query, (video,))
            owner = cursor.fetchone()

            if owner is not None:
                id = owner[0]
                owner = owner[1]
                videos.append((video, owner, id))

        return render_template('landing.html', name=session["Username"], videos=videos)
    else:
        return render_template('index.html', error="Invalid Credentials")

#
@app.route("/delete/<id>", methods=['GET'])
def delete(id):
    query = "SELECT Path_To_Video FROM Video_files WHERE Owner=(%s) AND Video_ID=(%s);"
    data = cursor.execute(query, (session["Username"], int(id)))
    result = cursor.fetchone()
    if request.cookies.get("ID") == ID and "ID" in session and result is not None:
        remove(UPLOAD_FOLDER + result[0])
        query = "DELETE FROM Video_files WHERE Owner=(%s) AND Video_ID=(%s);"
        data = cursor.execute(query, (session["Username"], int(id)))
        db_connector.commit()
    return redirect('/landing')
#
@app.route("/get_id/<name>", methods=['GET'])
def get_id(name):
    if request.cookies.get("ID") == ID and "ID" in session:
        query = "SELECT Video_ID FROM Video_files WHERE Path_To_Video='" + unquote(name) + "';"
        warning(query)
        data = cursor.execute(query)
        result = cursor.fetchone()
        if(result == None):
            return{ "id": -1 }
        else:
            return { "id": int(result[0]) }
    else: 
        return redirect('/login')
#
@app.route("/upload_link", methods=['POST'])
def upload_link():
    if request.cookies.get("ID") == ID and "ID" in session:
        if 'linkfile' in request.form:
            filename = request.form["linkfile"].split("/")[-1]
            system("wget --directory-prefix=" + app.config['UPLOAD_FOLDER'] + " " + request.form["linkfile"])
            #urlretrieve(request.form["linkfile"], path.join(app.config['UPLOAD_FOLDER'], filename))
            query = "INSERT INTO Video_files (Owner, Path_To_Video) VALUES (%s, %s);"
            data = cursor.execute(query, (session["Username"], filename))
            db_connector.commit()
            return redirect('/landing')
        else:
            return redirect('/landing_this_doesnt_exist.html')
    return redirect('/landing')


@app.route("/upload", methods=['POST'])
def upload():
    if request.cookies.get("ID") == ID and "ID" in session:
        if(request.method == 'POST'):
            if('file' not in request.files):
                flash('No file')
                return redirect(request.url)
            file = request.files['file']
            if file.filename == '':
                flash("No file")
                return redirect(request.url)
            if file:
                filename = file.filename
                file.save(path.join(app.config['UPLOAD_FOLDER'], filename))
                query = "INSERT INTO Video_files (Owner, Path_To_Video) VALUES (%s, %s);"
                data = cursor.execute(query, (session["Username"], filename))
                db_connector.commit()
                return redirect('/landing')
            else:
                return redirect(request.url)


@app.route("/video/<file>", methods=['GET', 'POST'])
def video(file):
    if request.cookies.get("ID") == ID and "ID" in session:
        return render_template("viewVideo.html", file="/static/videos/"+file, name=file)
    else:
        return render_template('index.html', error="Invalid Credentials")

#
@app.route("/logout", methods=['GET'])
def logout():
    if request.cookies.get("ID") == ID and "ID" in session:
        session.pop("ID", None)
        session.pop("Username", None)
        return render_template('index.html', error="Logged Out")
    else:
        return render_template('index.html', error="Invalid Credentials")

#
@app.route("/getVideo/<path:filename>", methods=['GET','POST'])
def getVideo(filename):
    if request.cookies.get("ID") == ID and "ID" in session:
        return send_file(filename, as_attachment=False)
    else:
        return redirect('/landing')

#
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False, ssl_context=('server.crt', 'server.key'))
