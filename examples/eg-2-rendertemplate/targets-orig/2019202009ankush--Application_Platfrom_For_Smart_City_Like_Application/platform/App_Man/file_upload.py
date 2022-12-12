from flask import Flask, redirect, url_for ,render_template,request
import sys
app = Flask(__name__)
import os
curpath=str(os.path.dirname(os.path.realpath(__file__)))
app = Flask(__name__, template_folder=curpath+'/templates')

@app.route("/sign-up",methods=["GET","POST"] )
def sign_up():
	print(request.form)
	if request.method=="POST":
		req=request.form
		req=dict(req)
		orig_stdout = sys.stdout
		f = open(curpath+"/file_up.txt", 'w')
		sys.stdout = f
		print(req)
		sys.stdout = orig_stdout
		f.close()
		# return (redirect(request.url))
		print("username -> ",req["user_id"])
		print("pwd -> ",req["pwd"])
		userid={}
		filename=curpath+"/name_password.txt"
		content=[]
		with open(filename) as f:
			content=f.readlines()
			content = [x.rstrip() for x in content] 
		for i in range(len(content)):
			s=content[i]
			y=[]
			y=s.split(":")
			userid[y[0]]=y[1]
		# print(userid)
		if req["user_id"] in userid.keys():
			if(userid[req["user_id"]]==req["pwd"]):
				tr="Valid"
			else:
				tr="Invalid"
		else:
			userid[req["user_id"]] = req["pwd"]
			tr="Valid"

		return render_template("index.html",messge=tr)

	return render_template("index.html")



@app.route("/upload",methods=["GET","POST"] )

def upload():
	if request.method=="POST":
		file=request.files['file']
		if not os.path.isdir(curpath+"/uploads"):
			os.mkdir(curpath+"/uploads")
		file.save(os.path.join(curpath+"/uploads", file.filename))
		return render_template("try.html",message="success")

	return render_template("try.html",message="upload")


if __name__ == "__main__":
    app.run(port=5555, debug=True)
