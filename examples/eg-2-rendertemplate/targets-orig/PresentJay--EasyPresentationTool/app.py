from flask import Flask, render_template, jsonify, redirect, session, url_for, request
from konlpy.tag import Kkma
import requests
import ko
import json

host_addr = "203.241.228.111"
#host_addr = "0.0.0.0"
port_num = "5050"

kkma = ko.Ko()
kkma.Process_KOR('아버지가 방에 들어가셨다')

app = Flask(__name__,static_url_path='/static')
app.secret_key = "super-secret-key"

@app.route("/")
def hello():
    return render_template("index.html")
    
@app.route("/result",methods=['POST','GET'])
def result():
    if request.method == 'POST':
        result = request.form
        return render_template("result.html",result=kkma.Process_KOR(result['str']))

@app.route("/edit",methods=['POST','GET'])
def edit():
    if request.method == 'POST':
        result = request.form
        arr = json.dumps(result['Sentence_Array'])
        #res = requests.post('http://203.241.228.111:9000', data = arr)
        res = requests.get('http://203.241.228.109:9000')
        #res = requests.get('http://203.241.228.109:3001/t', data = 'test')
        #headers = {'Content-Type': 'application/json; charset=utf-8'}
        #res = requests.post('http://203.241.228.109:9000',headers=headers, data=arr)
        return redirect('http://203.241.228.109:9000') 

        #render_template("edit.html")

if __name__ == "__main__":
    #app.run(host=host_addr,port=port_num)
    app.run(host=host_addr,port=port_num,debug=True)
