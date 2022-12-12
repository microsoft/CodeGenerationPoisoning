import json
import argparse
from dispatch_backend.DispatchController import DispatchController
from flask import Flask, request, render_template
app = Flask(__name__)

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int)

dispatch_controller: DispatchController = None

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/set_lan_configs", methods=["POST"])
def set_lan_configs():
    data = request.json
    try:
        response_dict = dispatch_controller.set_lan_configs(data)
        return json.dumps(response_dict)
    except Exception as e:
        print(e)
        return json.dumps({"status": "ERROR"})

@app.route("/get_lan_configs", methods=["POST"])
def get_lan_configs():
    data = request.json
    try:
        response_dict = dispatch_controller.get_lan_configs(data)
        return json.dumps(response_dict)
    except Exception as e:
        print(e)
        return json.dumps({"status": "ERROR"})

@app.route("/apc_record", methods=["POST"])
def record():
    data = request.json
    try:
        response_dict = dispatch_controller.push_apc_record(data)
        return json.dumps(response_dict)
    except:
        return json.dumps({"status": "ERROR"})

@app.route("/refresh", methods=["GET"])
def get_latest_records():
    try:
        response_dict = dispatch_controller.get_latest_apc_records()
        return json.dumps(response_dict)
    except Exception as e:
        print(e)
        return json.dumps({"status": "ERROR"})

if __name__ == "__main__":
    dispatch_controller = DispatchController()
    args = parser.parse_args()
    app.run(host="localhost", port=args.port)