from flask import Blueprint
from flask import Flask, abort
from flask import jsonify
from flask import render_template
from flask import request,send_from_directory
import jsonpickle
import json
import requests
import config as conf
import helpers
import os

grocery_api = Blueprint('grocery_api', __name__)


@grocery_api.route('', methods=['GET'])
def ask_for_image():
    return render_template('grocery/grocery.html')


@grocery_api.route('/upload', methods=['POST'])
def upload():
    global processed_images
    APP_ROOT = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(APP_ROOT, conf.grocery['dir'])

    if not os.path.isdir(target):
        os.mkdir(target)
    else:
        print("directory already present: {}".format(target))

    print('Upload')
    f = request.files
    destination = ''
    for upload in request.files.getlist("fileToUpload"):
        print(type(upload))
        print("{} is the file name".format(upload.filename))
        filename = upload.filename
        # destination = "/".join([target, "temp.jpg"])
        destination = "/".join([target, filename])
        print("Accept incoming file:", filename)
        print("Save it to:", destination)
        # print(upload.read())
        upload.save(destination)

    test_url = conf.grocery['url']

    # prepare headers for http request
    content_type = 'application/json'
    headers = {'content-type': content_type}

    list = {'image_list': destination}

    # send http request with image and receive response
    response = requests.post(test_url, data=jsonpickle.encode(list), headers=headers)
    # decode response
    print(json.loads(response.text))

    im_name = os.path.basename(destination)
    im_name_out1 = im_name.split('.')[0]+'_out1.jpg'
    im_name_out2 = im_name.split('.')[0]+'_out2.jpg'
    processed_images = [im_name, im_name_out1, im_name_out2]
    return render_template("grocery/grocery_gallery.html",image_names=processed_images)

@grocery_api.route('/static', methods=['POST'])
def for_static():
    global processed_images
    r = request
    data = r.data

    destination = jsonpickle.decode(data.decode('utf-8'))['image_list']

    data = {'image_list': os.path.join(conf.grocery['dir'], destination)}
    
    test_url = conf.grocery['url']

    # prepare headers for http request
    content_type = 'application/json'
    headers = {'content-type': content_type}


    # send http request with image and receive response
    response = requests.post(test_url, data=jsonpickle.encode(data), headers=headers)
    # decode response
    print(json.loads(response.text))


    im_name = os.path.basename(destination)
    im_name_out1 = im_name.split('.')[0]+'_out1.jpg'
    im_name_out2 = im_name.split('.')[0]+'_out2.jpg'
    processed_images = [im_name, im_name_out1, im_name_out2]
    print("********************")
    return render_template("grocery/grocery_gallery.html", image_names=processed_images)

@grocery_api.route('/processed')
def show_processed():
    return render_template("grocery/grocery_gallery.html", image_names=processed_images)


@grocery_api.route('/upload/<filename>')
def send_image(filename):
    return send_from_directory(conf.grocery['dir'], filename)

