import os
import pandas as pd
from flask import Flask,render_template,request

app= Flask(__name__)

@app.route('/', methods=['GET','POST'])
def hello():
    if request.method=="POST":
        file=request.files["file"]
        data = pd.read_csv(file)
        file.save(os.path.join("uploads",file.filename))
        return render_template("index2.html", message=data)
    return render_template("index2.html",message="upload")


if __name__=='__main__':
    app.run(debug=True)
