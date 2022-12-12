from flask import Flask, render_template ,request, Blueprint, flash,redirect,send_from_directory
from werkzeug import secure_filename
import os
from project import project
from project.countletters import countalpha


countletters = Blueprint('countletters', __name__)
UPLOAD__TEXT_FOLDER = '..'
This_Folder= os.path.dirname(os.path.abspath(__file__)) + '/textfiles'

# Used for uploading text files
@countletters.route('/<filename>')
def get_file(filename):
    return send_from_directory(This_Folder,filename)

# count the letters in the text file
@countletters.route('/countalpha', methods=['GET','POST'])
def count():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        # if the image is valid, do the following
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Create a path to the image in the upload folder, save the upload
            # file to this path
            textfile = (os.path.join(This_Folder, filename))
            file.save(textfile)
            # print('this is:', save_old)
            output = countalpha.countletter(textfile)

            return render_template('countalpha_Results.html', title='Count Letters Result!', output=output)
    return render_template('countalpha.html', title='Count Letters')


'''If there are multiple upload folder,s extensions cound't be the same'''
# allowed file types
TEXT_EXTENSIONS = {'txt'}
project.config['TEXT_EXTENSIONS']=TEXT_EXTENSIONS

# is file allowed to be uploaded?
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in project.config['TEXT_EXTENSIONS']