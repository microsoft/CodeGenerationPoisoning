from flask import Flask 
from flask_socketio import SocketIO, send
from flask import render_template
from modded_inference import getResponse

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecret'
socketio = SocketIO(app)

@socketio.on('message')
def handleMessage(msg):
	print("msg received by the server ",msg)
	if msg == "User has connected!":
		return;
	# if(msg === "User has connected!") {
	# 	return false;
	# }
	reply = getResponse(msg)
	print("Server responded : ",reply)
	send(reply, broadcast=True)

@app.route('/') 
# ‘/’ URL is bound with hello_world() function. 
def hello_world(): 
	#socketio.run(app,debug=True)
	return render_template('index.html')

if __name__ == '__main__':
	print("here")
	socketio.run(app,debug=True)
	#app.run()