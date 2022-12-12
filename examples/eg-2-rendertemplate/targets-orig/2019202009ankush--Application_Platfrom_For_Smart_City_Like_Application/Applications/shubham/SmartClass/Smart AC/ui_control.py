from flask import Flask, redirect, url_for ,render_template,request
#import webbrowser
import os

#webbrowser.open('http://127.0.0.1:5000/')
# from test import i,name,age

# from ac_temp import run
# import ac_temp

# print(display)
# print(i)


app = Flask(__name__)

@app.route("/sac")
def dashboard():
	curpath=str(os.path.dirname(os.path.realpath(__file__)))
	file=open(curpath+"/display.txt","r+")
	display=file.read()
	print("out_put 	RECEIVED",display)
	return render_template("ui_ac_control.html",name=display)


if __name__ == "__main__":
    app.run(port=5003, debug=True)


