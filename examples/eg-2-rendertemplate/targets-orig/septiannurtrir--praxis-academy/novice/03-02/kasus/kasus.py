import os
from flask import Flask, render_template, request, make_response, session, url_for, redirect, flash, abort

from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'wohohoho'

#upload
ALLOWED_EXTENSION = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
app.config['UPLOAD_FOLDER'] ='uploads'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSION

@app.route('/uploadfile', methods=['GET', 'POST'])
def uploadFile():
    if request.method == 'POST':

        file = request.files['file']

        if 'file' not in request.files:
            return redirect(request.url)

        if file.filename == '':
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return 'file berhasil disave di...' + filename

    return render_template('upload.html')