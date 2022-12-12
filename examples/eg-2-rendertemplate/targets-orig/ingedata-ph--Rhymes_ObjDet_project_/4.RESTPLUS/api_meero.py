from flask import  Flask, Blueprint, render_template, request,flash, redirect, url_for, send_from_directory,jsonify
from flask_restplus import Resource, Api
from flask import request
from werkzeug import secure_filename
import io , os
from werkzeug.datastructures import FileStorage
from api.gan.logic.tf_serving_sicara_client import make_prediction, format_mask
from api.gan.logic.utils.fonction_util import mask_to_polyg, convert_bbox

from object_detection.utils import visualization_utils as vis_util
from object_detection.utils import label_map_util

import numpy as np
from PIL import Image

import json
from google.protobuf.json_format import MessageToDict

import settings
import utils

import datetime
now = datetime.datetime.now()

app = Flask(__name__)
app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'

#app.register_blueprint(blueprint)
app.config['UPLOAD_FOLDER'] = 'upload_folder/'



def __get_flask_server_params__():
    '''
    Returns connection parameters of the Flask application

    :return: Tripple of server name, server port and debug settings
    '''
    server_name = utils.get_env_var_setting('FLASK_SERVER_NAME', settings.DEFAULT_FLASK_SERVER_NAME)
    server_port = int(utils.get_env_var_setting('FLASK_SERVER_PORT', settings.DEFAULT_FLASK_SERVER_PORT))
    flask_debug = utils.get_env_var_setting('FLASK_DEBUG', settings.DEFAULT_FLASK_DEBUG)

    flask_debug = True if flask_debug == '1' else False

    return server_name, server_port, flask_debug


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    uploaded_files = request.files.getlist("file")
    
    # upload label_map.pbtxt
    label_map_path= request.files["txtfile"]
    print (label_map_path)
    label_map_name = secure_filename(label_map_path.filename)
    path_to_labels=os.path.join(app.config['UPLOAD_FOLDER'], label_map_name)
    label_map_path.save(path_to_labels)


    # final_result=[]
    if not os.path.exists('output'):
        os.mkdir('output')
    # if os.path.isdir(json_save_path):
    saved_image=[]
    i=0
    for image_file in uploaded_files:
        #print((image_file.read())) ## type == bytes
        print("\n \n   n1 " + str( image_file))
        filename = secure_filename(image_file.filename)
        ## If you want to vizualize input image
        image_path=os.path.join(app.config['UPLOAD_FOLDER'], filename)
        print(f'\n\nSaving image to {image_path}\n\n')
        image_file.save(image_path)

        with open(image_path, 'rb') as f:
                image = f.read()

        ### Preparing Json file
        output_with_no_extension=filename.split('.', 1)[0]
        output_json = ''.join(['output/',output_with_no_extension,'_meero_out', '.json'])
        
        print("\n\n Make predition for {}\n\n " .format (filename))
        # result = make_prediction(image_file.read())
        num_detections,boxes,classes,scores,instance_masks,image_np=make_prediction(image,image_path)      
        
        #saved_image.append(filename)

        category_index = label_map_util.create_category_index_from_labelmap(path_to_labels,
                                                        use_display_name=True)

        #Create dictionary for json output
        coco_data = dict(
                info=dict(
                    description=None,
                    url=None,
                    version=None,
                    year=now.year,
                    contributor="Yraimtj",
                    date_created=now.strftime('%Y-%m-%d %H:%M:%S.%f'),
                ),
                identifications=[
                ],
            )
        
        for index , score in enumerate (scores):
            if score >= 0.7 :
                if instance_masks is None:
                    polygone = None
                else:
                    polygone = mask_to_polyg(instance_masks[index])
                coco_data['identifications'].append(dict(
                    data= convert_bbox (image_path,boxes[index].tolist()) #[xmin,xmax,ymin,ymax] #boxes[index].tolist()# boxes
                    , 
                    type='boundingBox', 
                    errors=[], 
                    category='Annotation', 
                    attributes= 
                        dict(label=category_index[classes[index]]['name']),###classes[index] #classes
                    proba=score,
                    polygone = polygone
                ))
                # print (classes[index])
                # print (category_index[classes[index]]['name'])
    
        coco_json = ''.join(['output/',output_with_no_extension,'_coco_out', '.json'])

        # results_json = [{'digit': res[0], 'probability': res[1]} for res in results]
        print(f'\n\nSaving output to {output_json}\n\n')

        # with open(output_json, 'w+') as outfile:
        #     json.dump(MessageToDict(result,preserving_proto_field_name = True), outfile)

        with open(coco_json, 'w') as f:
            json.dump(coco_data,f,indent=4)

        #     Process predict Image

        predict_image=''.join([output_with_no_extension,'_out_mask', '.jpeg'])
        output_image=os.path.join(app.config['UPLOAD_FOLDER'], predict_image)
        
        vis_util.visualize_boxes_and_labels_on_image_array(
            image_np,
            boxes,
            classes,
            scores,
            category_index,
            instance_masks=instance_masks,
            use_normalized_coordinates=True,
            line_thickness=8)
        Image.fromarray(image_np).save(output_image)
        saved_image.append(predict_image)
        print('\n\nImage saved\n\n')
        #print(i)
        i+=1

    print(saved_image)
    #return jsonify(result=results_json)
    doc_images=os.listdir('./doc')
    return render_template("gallery.html",image_names = saved_image,decorate_images= doc_images)
    # else:
    #     flash(f'The {json_save_path} path did not exist', 'danger')
    # return redirect(url_for('index')) 


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    # IMAGE_SIZE = (12, 8)
    return send_from_directory(app.config['UPLOAD_FOLDER'],filename)

@app.route('/gallery/<filena>')
def get_gallery(filena):
    # final_result=showed_images
    # image_names=os.listdir('./doc')
    return send_from_directory("doc",filena)


if __name__ == '__main__':
    server_name, server_port, flask_debug = __get_flask_server_params__()
    app.run(debug=flask_debug, host=server_name, port=server_port)


