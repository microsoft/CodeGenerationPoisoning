#!/usr/bin/env python


"""
.. module:: main
   :synopsis: Manages all the redirections, contains the logic that can't be put in tools.
.. moduleauthor:: Romain Boureau
"""


from pprint import pprint as pp
from flask import Flask, flash, redirect, render_template, request, url_for, send_file
from tools import query_api, fusionImages
from PIL import Image
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static'
@app.route('/')
def index():

     """

        **Homepage**
        
        This function is used to display the homepage of the web-app.

        :return: redirection to challengeHomepage.html
    """

     
     return render_template('challengeHomepage.html')
@app.route("/result" , methods=['GET', 'POST'])
def result():

     """

        **Form exploitation and Result**
        
        This function is used to manage the form submitted by the user in challengeHomePage.
        It uses 3 elements from the submitted form ::

               - latitude in the [-90,90] range

               - longitude in the [-180,180] range

               - fileupload which is the image used to overlay the satellite image from the Google API.

        With these elements, it uses the tools functions to get the satellite image and create the overlaid image.

        Once the tools are used, it simply redirects to result.html that will display the overlaid image.

        :return: redirection to result.html
    """
     data = []
     error = None
     request_file = request.files['fileupload']
     if not request_file:
          return "No file"
     request_file.save(os.path.join(app.config['UPLOAD_FOLDER'],"plume.png"))
     latitude = request.form.get('latitude')
     longitude = request.form.get('longitude')
     query_api(latitude,longitude,"./static/img.png")
     resp = fusionImages("./static/img.png","./static/plume.png","./static/fusioned.png")
     
     pp(resp)
     

     return render_template(
               'result.html',
               error=error)
@app.route("/api/image", methods=['POST'])
def getRequestFromImage():
     """

        **Overlaid Image RESTful API**
        
        This function is a custom made RESTful API.

        The URI is http://127.0.0.1:5000/api/image and it uses the POST method.

        It's very close to the result() function, however the returned value is different.

        It uses 3 elements from the submitted request ::
        
               - latitude in the [-90,90] range

               - longitude in the [-180,180] range

               - fileupload which is the image used to overlay the satellite image from the Google API.

        With these elements, it uses the tools functions to get the satellite image and create the overlaid image.

        Once the tools are used, it sends back the png image with send_file.

        :return: the overlaid image using send_file
    """
     request_file = request.files['fileupload']
     if not request_file:
          abort(400);
     request_file.save(os.path.join(app.config['UPLOAD_FOLDER'],"plume.png"))
     latitude = float(request.form.get('latitudeH'))
     longitude = float(request.form.get('longitudeH'))
     query_api(latitude,longitude,"./static/img.png")
     resp = fusionImages("./static/img.png","./static/plume.png","./static/fusioned.png")
     try:
          return send_file("static/fusioned.png", mimetype='image/png')
     except FileNotFoundError:
        abort(404)
        
if __name__=='__main__':    app.run(debug=True)
