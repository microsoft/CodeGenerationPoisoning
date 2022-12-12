from flask import Flask
from flask import request
from flask import render_template
from wtforms import Form
import subprocess
app = Flask(__name__)
@app.route('/', methods=('GET', 'POST'))
def index():
    return render_template("index.html")

@app.route('/turnon/', methods=['POST'])
def move_forward():
    forward_message = "Moving forward..."
    subprocess.Popen("./send_command.sh")
    print("THIS IS A TEST")
    return render_template('index.html')

@app.route('/turnoff/', methods=['POST'])
def move_backward():
    subprocess.Popen("./send_stop.sh")
    print("THIS IS A STOP")
    return render_template('index.html')
