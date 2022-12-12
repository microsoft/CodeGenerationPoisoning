import os
import helper
import mydb
from flask import Flask, render_template, request, jsonify, send_file
from flask_json import FlaskJSON, JsonError, json_response
import face_recognition
import cv2
import base64
import ast

app = Flask(__name__)
APP_ROOT = "/home/rsa-key-20200109/my_flask_app"
target_gallery = os.path.join(APP_ROOT, 'static/images/gallery')
target_temp = os.path.join(APP_ROOT, 'static/images/temp')

@app.route("/")
def index():
    return render_template("upload.html")


@app.route("/upload", methods=['POST'])
def upload():
    print("/upload")
    encodedImg = request.form['file']
    image_file = helper.decode_and_save_image_and_return_file(encodedImg, target_temp)

    # Save image in temp folder
    # need to remove the line below
    #print("type(image_file)")
    #print(type(image_file))
    #print("image_file")
    #print(image_file)
    #temp_image_file = helper.save_image_first_time(image_file, target_temp)
    # Save in DB - temp image, location and datetime
    full_path_of_image = helper.get_path_image(image_file, target_temp)
    datetime = request.form['datetime']
    location = request.form['location']
    # insert DB
    image_id = mydb.insert_all_pictuers(full_path_of_image, datetime, location)
    print("Check if there are faces at image")
    # Check if there are faces at image
    if helper.is_there_a_face_in_the_image(full_path_of_image):
        # if have - check if know
        # check_known = helper.is_the_face_known(full_path_of_image)
        check_known = helper.is_the_face_known(full_path_of_image)
        # if know save at gallery and remove from temp and update galley DB (know, new path)
        if check_known['all_knowns']:
            # Save image in gallery folder
            new_path = helper.save_image(image_file, target_gallery)
            # delete from temp folder
            os.remove(full_path_of_image)
            # update path in db
            mydb.update_path_original_image(image_id, new_path)
            
            # image = face_recognition.load_image_file(new_path)
            # face_location = face_recognition.face_locations(image, number_of_times_to_upsample=2)
            names = ""
            knowns = []
            face_locations = []
            for i in range(len(check_known['list_knowns'])):
                known = check_known['list_knowns'][i]
                knowns.append(known['name'])
                face_locations.append(known['face_location'])
                name = known['name']
                names += name + " "
                
            mydb.insert_pictuers_with_face(image_id, face_locations, knowns)
            names = names.strip()
            # convert server path to client path of image
            client_path_image = helper.convert_server_path_to_client_path_image(new_path)
            return jsonify(action="show image", knowns=names, path_image=client_path_image, image_id=image_id)
        # else if no know but have face - asking from user name to face with id of image in gallrey db
        else:
            return jsonify(action="ask name", image_id=image_id, list_knowns=check_known['list_knowns'], list_unknowns=check_known['list_unknowns'], image=check_known['image'])

    # else if no face at image - move image to gallrey folder and update gallery DB (path)
    new_path = helper.save_image(image_file, target_gallery)
    mydb.update_path_original_image(image_id, new_path)
    os.remove(full_path_of_image)
    return jsonify(action="show image", image_id=image_id )


@app.route("/askName", methods=['GET'])
def askName():
    return render_template("get_name.html")


@app.route("/enterName", methods=['POST'])
def enterName():
    name_faces = request.form['inputNames']
    image_id = request.form['galleryId']
    face_locations = request.form['facesLocation']

    # Convert string list to list
    name_faces_list = name_faces.strip('][').split(', ')
    face_locations_list = face_locations.strip('][').split(', ')
    # cut face from original image and save in knowns folder
    path_original_image = mydb.get_image_path_by_id(image_id)
    # insert to db
    mydb.insert_pictuers_with_face(image_id, face_locations_list, name_faces_list)
    
    # move original image to gallrey folder
    if not os.path.isdir(target_gallery):
        os.mkdir(target_gallery)
    new_path = "/".join([target_gallery, path_original_image.split('/')[-1]])
    # update gallery DB (path)
    mydb.update_path_original_image(image_id, new_path)
    
    os.rename(path_original_image, new_path)
    return jsonify(action="show image", image_id=image_id)


@app.route("/showImage/<id>", methods=['GET'])
def showImage(id):
    print("----------------------------")
    print(mydb.is_there_a_face(id))
    print("----------------------------")
    if mydb.is_there_a_face(id)==0: 
        result=mydb.no_face_show(id)
    else:
        result = mydb.get_full_details_of_image(id)
    
    result["path"] = helper.convert_server_path_to_client_path_image(result["path"])
    return jsonify( result )


@app.route("/showImages", methods=['GET'])
def showImages():
    results = mydb.get_list_of_pictuers()
    for child in results:
        child["path"] = helper.convert_server_path_to_client_path_image(child["path"])
    return jsonify(results)

@app.route("/search/<name_person>", methods=['GET'])
def search(name_person):
    results = mydb.get_list_of_pictuers_by_name_known(name_person)
    for child in results:
        child["path"] = helper.convert_server_path_to_client_path_image(child["path"])
    return jsonify(results)

#finished till here update of db need to continue from here.
@app.route("/delete/<gallery_id>", methods=['DELETE'])
def delete(gallery_id):
    image_path = mydb.get_image_path_by_id(gallery_id)
    mydb.delete_from_all_pictuers(gallery_id)
    try:
        os.remove(image_path)
    except:
        return jsonify(action="Fail")

    return jsonify(action="done")
