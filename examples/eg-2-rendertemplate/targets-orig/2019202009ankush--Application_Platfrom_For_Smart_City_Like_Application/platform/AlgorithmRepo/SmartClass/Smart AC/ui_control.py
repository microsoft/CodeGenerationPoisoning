from flask import Flask, redirect, url_for ,render_template,request
import webbrowser

webbrowser.open('http://127.0.0.1:3333/')
# from test import i,name,age

# from ac_temp import run
# import ac_temp

# print(display)
# print(i)


app = Flask(__name__)

@app.route("/")

def dashboard():
	
	file=open("display.txt","r+")
	display=file.read()
	print("out_put 	RECEIVED",display)
	return render_template("ui_ac_control.html",name=display)


if __name__ == "__main__":
    app.run(port=3333, debug=True)


