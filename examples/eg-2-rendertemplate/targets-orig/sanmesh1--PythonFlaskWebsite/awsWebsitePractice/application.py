###########################################################################
import os
from flask import Flask, flash, request, redirect, url_for
from werkzeug.utils import secure_filename
##from clusterImage import clusterImage
from flask import render_template

UPLOAD_FOLDER = 'static/upload'
ALLOWED_EXTENSIONS = {'jpg'}

application = Flask(__name__)
application.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

###########################################################################
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.metrics import pairwise_distances_argmin
from sklearn.datasets import load_sample_image
from sklearn.utils import shuffle
from time import time
##import quantizeRGB

def clusterImage(imageName, k_rgb1):

    ##quantizeRGB#####################################
    #k_rgb1 = 8
    #imageName = 'beautiful'

    #load image
    img1 = np.array(plt.imread(imageName + '.jpg'))
    img2 = np.array(plt.imread(imageName + '.jpg'))
    imgCopy = np.array(plt.imread(imageName + '.jpg'))

    quantizeRGBImg1, quantizeRGBmeanColors1 = np.array(quantizeRGB(img1, k_rgb1))
    clusteredFileName = imageName+'_kmeansIs'+str(k_rgb1)+'.jpg'
    plt.imsave(clusteredFileName, quantizeRGBImg1)
    return clusteredFileName

###########################################################################

import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.metrics import pairwise_distances_argmin
from sklearn.datasets import load_sample_image
from sklearn.utils import shuffle
from time import time

#parts of code taken from https://scikit-learn.org/stable/auto_examples/cluster/plot_color_quantization.html

def quantizeRGB(origImg, k):
    ### Convert to floats instead of the default 8 bits integer coding. Dividing by
    ### 255 is important so that plt.imshow behaves works well on float data (need to
    ### be in the range [0-1])
    origImg = np.array(origImg, dtype=np.float64) / 255

    # Load Image and transform to a 2D numpy array.
    w, h, d = original_shape = tuple(origImg.shape)
    image_array = np.reshape(origImg, (w * h, d))
    kmeans = KMeans(n_clusters=k, random_state=0).fit(image_array)

    def recreate_image(codebook, labels, w, h):
        """Recreate the (compressed) image from the code book & labels"""
        d = codebook.shape[1]
        image = np.zeros((w, h, d))
        label_idx = 0
        for i in range(w):
            for j in range(h):
                image[i][j] = codebook[labels[label_idx]]
                label_idx += 1
        return image


    outputImg = (255*recreate_image(kmeans.cluster_centers_, kmeans.labels_, w, h)).astype('uint8')
    meanColors = kmeans.cluster_centers_*255
    return outputImg, meanColors

####################################################################################

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@application.route('/', methods=['GET', 'POST'])
def upload_file():
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
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <br>
      Number of Clusters: <input type="number" name="quantity" min="1" max="30">
      <br>
      <input type=submit value=Upload>
    </form>
    '''
from flask import send_from_directory

@application.route('/uploads/<filename>/<clusters>')
def uploaded_file(filename, clusters):
##    clusters = 3
    clusters = int(clusters)
    print("filename", filename)
    clusteredFileName = clusterImage("static/upload/"+filename[0:-4], clusters)
    print(clusteredFileName)
    print('/' + "static/upload/"+filename)
    return render_template("uploaded.html", input_image = '/' + "static/upload/"+filename, clustered_image =  '/' + clusteredFileName)
if __name__ == "__main__":
    application.debug = True
    application.run()	

##########################################################################################3

##from flask import Flask
##
### print a nice greeting.
##def say_hello(username = "World"):
##    return '<p>Hello %s!</p>\n' % username
##
### some bits of text for the page.
##header_text = '''
##    <html>\n<head> <title>EB Flask Test</title> </head>\n<body>'''
##instructions = '''
##    <!doctype html>
##    <title>Upload new File</title>
##    <h1>Upload new File</h1>
##    <form method=post enctype=multipart/form-data>
##      <input type=file name=file>
##      <br>
##      Number of Clusters: <input type="number" name="quantity" min="1" max="30">
##      <br>
##      <input type=submit value=Upload>
##    </form>'''
##home_link = '<p><a href="/">Back</a></p>\n'
##footer_text = '</body>\n</html>'
##
### EB looks for an 'application' callable by default.
##application = Flask(__name__)
##
### add a rule for the index page.
##application.add_url_rule('/', 'index', (lambda: header_text +
##    say_hello() + instructions + footer_text))
##
### add a rule when the page is accessed with a name appended to the site
### URL.
##application.add_url_rule('/<username>', 'hello', (lambda username:
##    header_text + say_hello(username) + home_link + footer_text))
##
### run the app.
##if __name__ == "__main__":
##    # Setting debug to True enables debug output. This line should be
##    # removed before deploying a production app.
##    application.debug = True
##    application.run()

##########################################################################################3

####from flask import Flask
####sys.path.append("/modules")
##import os
##from flask import Flask, flash, request, redirect, url_for
##from werkzeug.utils import secure_filename
####from clusterImage import clusterImage
##from flask import render_template
##
##
### print a nice greeting.
##def say_hello(username = "World"):
##    return '<p>Hello %s!</p>\n' % username
##
### some bits of text for the page.
##header_text = '''
##    <html>\n<head> <title>EB Flask Test</title> </head>\n<body>'''
##instructions = '''
##    <!doctype html>
##    <title>Upload new File</title>
##    <h1>Upload new File</h1>
##    <form method=post enctype=multipart/form-data>
##      <input type=file name=file>
##      <br>
##      Number of Clusters: <input type="number" name="quantity" min="1" max="30">
##      <br>
##      <input type=submit value=Upload>    '''
##home_link = '<p><a href="/">Back</a></p>\n'
##footer_text = '</body>\n</html>'
##
### EB looks for an 'application' callable by default.
##application = Flask(__name__)
##
###add a rule for the index page.
##@application.route('/', methods=['GET', 'POST'])
##def upload_file():
####    if request.method == 'POST':
####        # check if the post request has the file part
####        if 'file' not in request.files:
####            flash('No file part')
####            return redirect(request.url)
####        file = request.files['file']
####        clusters = request.form['quantity']
####        print(clusters)
####        # if user does not select file, browser also
####        # submit an empty part without filename
####        if file.filename == '':
####            flash('No selected file')
####            return redirect(request.url)
####        if file and allowed_file(file.filename):
####            filename = secure_filename(file.filename)
####            file.save(os.path.join(application.config['UPLOAD_FOLDER'], filename))
####            return redirect(url_for('uploaded_file',
####                                    filename=filename, clusters = clusters))
##    return '''
##    <!doctype html>
##    <title>Upload new File</title>
##    <h1>Upload new File</h1>
##    <form method=post enctype=multipart/form-data>
##      <input type=file name=file>
##      <br>
##      Number of Clusters: <input type="number" name="quantity" min="1" max="30">
##      <br>
##      <input type=submit value=Upload>
##    </form>
##    '''
##
##
### add a rule when the page is accessed with a name appended to the site
### URL.
##application.add_url_rule('/<username>', 'hello', (lambda username:
##    header_text + say_hello(username) + home_link + footer_text))
##
### run the app.
##if __name__ == "__main__":
##    # Setting debug to True enables debug output. This line should be
##    # removed before deploying a production app.
##    application.debug = True
##    application.run()
