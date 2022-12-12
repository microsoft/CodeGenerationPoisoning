#https://overiq.com/flask/0.12/form-handling-in-flask/
from flask import Flask, render_template, request, send_from_directory
import os,signal,sys
import config
import rospy
from traversal.msg import WheelRpm

app = Flask(__name__)
config.configure_app(app)

rospy.init_node('drive_joy_gui')
pub = rospy.Publisher('motion', WheelRpm,queue_size=1)   

@app.route('/',methods=['GET', 'POST'])
def index():
	
	if request.method == 'POST':
		msg = WheelRpm()
		if not (request.form.get('x') == None):
		  msg.omega =  int(50*float(request.form.get('x')))
		  msg.vel = int(50*float(request.form.get('y')))
		  if int(request.form.get('hb')) == 1:
			msg.hb = True
		  pub.publish(msg)
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

def signal_handler(signal, frame):  #For catching keyboard interrupt Ctrl+C
	print "\nProgram exiting....."
	sys.exit(0)

if __name__ == '__main__':
	signal.signal(signal.SIGINT, signal_handler)
	app.run(host='0.0.0.0',port=1272,debug=True, threaded=True)
	

	
	
  
	
	
	
