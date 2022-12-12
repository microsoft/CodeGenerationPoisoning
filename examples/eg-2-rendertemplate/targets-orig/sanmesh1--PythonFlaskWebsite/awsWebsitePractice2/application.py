###########################################################################
########imports
###########################################################################
import os
from flask import Flask, flash, request, redirect, url_for
from werkzeug.utils import secure_filename
from flask import render_template
from kmeansClusterRGB import kmeansClusterRGBRawImage, kmeansClusterRGBImagePath

###########################################################################
########Flask Setup
###########################################################################
UPLOAD_FOLDER = 'static'
ALLOWED_EXTENSIONS = {'jpg', 'png'}
application = Flask(__name__)
application.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
application.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024    # 2 Mb limit

###########################################################################
########Functions
###########################################################################
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
                    
###########################################################################
########Routes
###########################################################################
########Function to handle uploading of file too big
@application.errorhandler(413)
def error413(e):
    return redirect(url_for('kmeansRGBOnImage'))

@application.route('/')
def index():
    return render_template('index.html')

@application.route('/kmeansRGBOnImage', methods=['GET', 'POST'])
def kmeansRGBOnImage():
    ##############################
    #clean files
    import os, time, sys
    print("Entered clean files")

    now = time.time()
    path = "static"
    numMinutes = 10

    for f in os.listdir(path):
        f1 = os.path.join(path, f)
        if (now - os.stat(f1).st_mtime) > 60*numMinutes:
            print(("Sanmesh1" in f), " directory ", f)
            if ("Sanmesh1" in f) == False and os.path.isfile(f1) and os.path.isdir(f1) == False and f1.lower().endswith(('.png', '.jpg', '.jpeg')):
                os.remove(f1)
    ###clean files
    ################################

    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        clusters = request.form['quantity']
        print(clusters)
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(application.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('uploaded_file',
                                    filename=filename, clusters = clusters))
    return render_template('kmeansRGBOnImage.html')

from flask import send_from_directory

@application.route('/uploads/<filename>/<clusters>')
def uploaded_file(filename, clusters):
    clusters = int(clusters)
    clusteredFileName = []
    if clusters != 0:
        clusteredFileName.append('/'+kmeansClusterRGBImagePath("static/"+filename, clusters))
        clusterList = [clusters]
##        print("filename", filename)
##        print('/' + clusteredFileName)
##        print('/' + "static/"+filename)
    else:
        clusterList = [3,6,9]
        for i in clusterList:
            clusteredFileName.append('/'+kmeansClusterRGBImagePath("static/"+filename, i))
    return render_template("uploaded.html", input_image = '/' + "static/"+filename, clusteredFileName = clusteredFileName, clusterList = clusterList)
##    return render_template("uploaded.html", input_image = '/' + "static/"+filename, clustered_image =  '/' + clusteredFileName)
if __name__ == "__main__":
    application.debug = True
    application.run()	

