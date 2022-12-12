from flask import send_from_directory
from flask import render_template
from flask import request
import os
from web.genDocx import doc_algo
from flask import Flask
import random
import string

app = Flask(__name__)




@app.route('/')
def hello_world():
    return render_template("index.html")


@app.route("/api/download/<path:filename>")
def download(filename):
    dirpath = os.path.join(app.root_path)
    print(dirpath)
    return send_from_directory(dirpath, filename, as_attachment=True)
    # as_attachment=True 一定要写，不然会变成打开，而不是下载


@app.route("/api/upload",methods=["GET","POST"])
def upload():
    if request.method == "GET":
        return "get"
    if request.method == "POST":
        name = ''.join(random.sample(string.ascii_letters + string.digits, 8)) + '.docx'
        print(request.form)
        form_dict = request.form
        form_dict = form_dict.to_dict()
        print(form_dict)
        #转换成字典
        doc_algo.main_algo_generate(form_dict,name)
        return name





