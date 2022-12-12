from flask import Flask, redirect, url_for ,render_template,request
import webbrowser
import os

webbrowser.open('http://127.0.0.1:3333/')
# from test import i,name,age

# from ac_temp import run
# import ac_temp

# print(display)
# print(i)
curpath=str(os.path.dirname(os.path.realpath(__file__)))
app = Flask(__name__, template_folder=curpath+'/templates')

@app.route("/")

def dashboard():
	curpath=str(os.path.dirname(os.path.realpath(__file__)))
	file=open(curpath+"/running.txt","r+")
	# file=open("running.txt","r+")
	x=file.read()

	
	# file=open("display.txt","r+")
	# display=file.read()
	print("out_put 	RECEIVED",x)
	return render_template("user_dashboard.html",status=x)


if __name__ == "__main__":
    app.run(port=3333, debug=True)


