##import os
##from flask import Flask, flash, request, redirect, url_for
##from werkzeug.utils import secure_filename
##from clusterImage import clusterImage
##from flask import render_template
##
##UPLOAD_FOLDER = 'static/upload'
##ALLOWED_EXTENSIONS = {'jpg'}
##
##application = Flask(__name__)
##application.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
##
##def allowed_file(filename):
##    return '.' in filename and \
##           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
##
##@application.route('/', methods=['GET', 'POST'])
##def upload_file():
##    if request.method == 'POST':
##        # check if the post request has the file part
##        if 'file' not in request.files:
##            flash('No file part')
##            return redirect(request.url)
##        file = request.files['file']
##        clusters = request.form['quantity']
##        print(clusters)
##        # if user does not select file, browser also
##        # submit an empty part without filename
##        if file.filename == '':
##            flash('No selected file')
##            return redirect(request.url)
##        if file and allowed_file(file.filename):
##            filename = secure_filename(file.filename)
##            file.save(os.path.join(application.config['UPLOAD_FOLDER'], filename))
##            return redirect(url_for('uploaded_file',
##                                    filename=filename, clusters = clusters))
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
##from flask import send_from_directory
##
##@application.route('/uploads/<filename>/<clusters>')
##def uploaded_file(filename, clusters):
####    clusters = 3
##    clusters = int(clusters)
##    print("filename", filename)
##    clusteredFileName = clusterImage("static/upload/"+filename[0:-4], clusters)
##    print(clusteredFileName)
##    print('/' + "static/upload/"+filename)
##    return render_template("uploaded.html", input_image = '/' + "static/upload/"+filename, clustered_image =  '/' + clusteredFileName)
##if __name__ == "__main__":
##    application.debug = True
##    application.run()	

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

##from flask import Flask
import os
from flask import Flask, flash, request, redirect, url_for
from werkzeug.utils import secure_filename
from clusterImage import clusterImage
from flask import render_template

# print a nice greeting.
def say_hello(username = "World"):
    return '<p>Hello %s!</p>\n' % username

# some bits of text for the page.
header_text = '''
    <html>\n<head> <title>EB Flask Test</title> </head>\n<body>'''
instructions = '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <br>
      Number of Clusters: <input type="number" name="quantity" min="1" max="30">
      <br>
      <input type=submit value=Upload>    '''
home_link = '<p><a href="/">Back</a></p>\n'
footer_text = '</body>\n</html>'

# EB looks for an 'application' callable by default.
application = Flask(__name__)

#add a rule for the index page.
@application.route('/', methods=['GET', 'POST'])
def upload_file():
##    if request.method == 'POST':
##        # check if the post request has the file part
##        if 'file' not in request.files:
##            flash('No file part')
##            return redirect(request.url)
##        file = request.files['file']
##        clusters = request.form['quantity']
##        print(clusters)
##        # if user does not select file, browser also
##        # submit an empty part without filename
##        if file.filename == '':
##            flash('No selected file')
##            return redirect(request.url)
##        if file and allowed_file(file.filename):
##            filename = secure_filename(file.filename)
##            file.save(os.path.join(application.config['UPLOAD_FOLDER'], filename))
##            return redirect(url_for('uploaded_file',
##                                    filename=filename, clusters = clusters))
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


# add a rule when the page is accessed with a name appended to the site
# URL.
application.add_url_rule('/<username>', 'hello', (lambda username:
    header_text + say_hello(username) + home_link + footer_text))

# run the app.
if __name__ == "__main__":
    # Setting debug to True enables debug output. This line should be
    # removed before deploying a production app.
    application.debug = True
    application.run()
