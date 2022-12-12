#https://overiq.com/flask/0.12/form-handling-in-flask/
from flask import Flask, render_template, request, send_from_directory
import os,signal,sys
import config


app = Flask(__name__)
config.configure_app(app)


@app.route('/',methods=['GET', 'POST'])
def index():
	return render_template('index.html')
	

@app.route('/img/button.png')
def anv1():
	return send_from_directory(os.path.join(app.root_path, 'static'),
							   'img/button.png')

@app.route('/img/canvas.png')
def anv2():
	return send_from_directory(os.path.join(app.root_path, 'static'),
							   'img/canvas.png')
							   
@app.route('/favicon.ico')
def favicon():
	return send_from_directory(os.path.join(app.root_path, 'static'),
							   'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/abc.png')
def anv3():
	return send_from_directory(os.path.join(app.root_path, 'static'),
							   'abc.png')

def signal_handler(signal, frame):  #For catching keyboard interrupt Ctrl+C
	print "\nProgram exiting....."
	sys.exit(0)

if __name__ == '__main__':
	signal.signal(signal.SIGINT, signal_handler)
	app.run(host='0.0.0.0',port=5000,debug=True, threaded=True)
	

	
	
  
	
	
	
