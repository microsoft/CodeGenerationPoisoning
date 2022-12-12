#https://overiq.com/flask/0.12/form-handling-in-flask/
from flask import Flask, render_template, request, send_from_directory
import os
import config

app = Flask(__name__)
config.configure_app(app)

drive = False
arm = False
a=0

@app.route('/',methods=['GET', 'POST'])
def index():
    global a
    global drive
    global arm
    if request.method == 'POST':
    
        if(request.form.get('drive')):
          drive = True
        else:
          drive = False
          
        if(request.form.get('arm')):
          arm = True
        else:
          arm= False
    print "gen"
    f = open("file.txt", "w")
    a = 1*int(drive) + 2*int(arm) 
    f.write(str(a))
    
    message = "Drive_" + str(drive) + "  |  Arm_" + str(arm)
    return render_template('index.html',message=message)
    
@app.route('/abc.png')
def anv():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'abc.png')
                               
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    app.run(host='127.127.127.127',port=1271,debug=True, threaded=True)

    
    
  
    
    
    
