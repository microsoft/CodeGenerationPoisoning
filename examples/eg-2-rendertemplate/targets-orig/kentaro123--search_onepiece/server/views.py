from flask import jsonify
from conf import *
from flask import Flask, render_template
from flask import request
from server.run_server import app
from server.module import KnowGraph
import json
import os



app = Flask(__name__)
app.debug = True

@app.route("/")
def index():
    return render_template("login.html")

"""
@app.route('/result',methods=["POST","GET"])
def look_up():
    kg = KnowGraph()
    client_params = request.form
    server_param = {}
    cont = kg.lookup_entry(client_params,server_param)
    return render_template("result.html",cont=cont)
"""

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
