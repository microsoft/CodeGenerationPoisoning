from flask import Flask, render_template ,request, Blueprint, flash,redirect,send_from_directory
from werkzeug import secure_filename
import os
import PIL
from PIL import Image
import PIL.ImageOps
from project import project
import cv2 as cv
from project.steg import desteg


UPLOAD__IMAGE_FOLDER = '..'

steg = Blueprint('steg', __name__)

Image_Folder= os.path.dirname(os.path.abspath(__file__))+'/images'

# Used for uploading pictures
@steg.route('/<filename>')
def get_file(filename):
    return send_from_directory(Image_Folder,filename)


# invert images
@steg.route('/image', methods=['GET', 'POST'])
def invert_file():
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
            save_old=(os.path.join(Image_Folder, filename))
            file.save(save_old)
            # print('this is:', save_old)
            # Take the image, make a new one that is inverted
            img = Image.open(save_old)
            rbg_img = img.convert('RGB')
            inverted_image = PIL.ImageOps.invert(rbg_img)

            save_new=(os.path.join(Image_Folder, 'new_'+filename))
            inverted_image.save(save_new)
            # Render template with inverted picture
            # rt = render_template('imageResults.html', filename='new_'+filename)
            # print('this is new_'+filename)
            return render_template('image_Results.html', title = 'Covert RGB Result!',filename='new_'+filename)
    return render_template('image.html', Title = 'Convert RGB')


# Steg image
#  /steg  This is for html path
@steg.route('/steg', methods=['GET', 'POST'])
# function name is for the action in html.
def steg_file():
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
            save_old=(os.path.join(Image_Folder, filename))
            file.save(save_old)
            # print('this is:', save_old)
            # read the image by using opencv
            # img = cv.imread(save_old, cv.IMREAD_COLOR)
            # send it to the function store in desteg file then return the result.
            message = request.form['inputtext']
            # print(message)
            msg2 = desteg.steg_message(save_old,message)
            filename = msg2
            # save_new = (os.path.join(project.config['UPLOAD__IMAGE_FOLDER'], 'new_' + filename)) -> ? how do i make this work
            # so i can return a image path to html and show it in HTML
            # print(filename2)
            return render_template('steg_Results.html', title = 'Steg Result', filename = filename)


# desteg images
@steg.route('/desteg', methods=['GET', 'POST'])
def desteg_file():
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
            save_old=(os.path.join(Image_Folder, filename))
            file.save(save_old)
            # print('this is:', save_old)
            # read the image by using opencv
            # img = cv.imread(save_old, cv.IMREAD_COLOR)
            # send it to the function store in desteg file then return the result.
            msg2 = desteg.desteg(save_old)

            return render_template('desteg_Results.html', title = 'Desteg Result', msg2=msg2)
    return render_template('desteg.html', title = 'Desteg the Images!!')





'''If there are multiple upload folder,s extensions cound't be the same'''
# allowed file types
IMAGE_EXTENSIONS = {'png','jpg','jpeg'}
project.config['IMAGE_EXTENSIONS']=IMAGE_EXTENSIONS

# is file allowed to be uploaded?
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in project.config['IMAGE_EXTENSIONS']





