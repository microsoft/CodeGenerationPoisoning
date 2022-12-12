from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from bson.json_util import dumps
from flask_bcrypt import Bcrypt
import json
import datetime
import pytz

uri = "mongodb://user:password@db:27017/"
Client = MongoClient(uri)
db = Client["SensorData"]
coll = db["Values"]

db_user = Client["user"]
coll_user = db_user["userdata"]

app = Flask(__name__)
bcrypt = Bcrypt(app)


@app.route("/", methods=["GET"])
def index():
    get_date = str(datetime.datetime.now(tz=pytz.timezone("Europe/Stockholm")).date())
    newest_entry = coll.find({"Date": get_date}).sort("Time", -1).limit(1)

    try_date = coll.count_documents({"Date": get_date})

    if try_date == 0:
        response = str("No data found")

    else:
        response = []
        for x in newest_entry:
            response.append(x)
    return render_template("index.html", date=get_date, newest=dumps(response))


@app.route("/user/login", methods=["POST"])
def login():

    username = request.authorization["username"]
    password = request.authorization["password"]

    response = coll_user.find_one({"username": username})
    if response:
        if bcrypt.check_password_hash(response["password"], password):
            return jsonify("Login test successful")

        else:
            return jsonify("invalid password")
    else:
        return jsonify("invalid username")


@app.route("/user/register", methods=["POST"])
def testing():
    check_user = coll_user.count_documents({})

    username_ = request.json["username"]
    password_ = bcrypt.generate_password_hash(request.json["password"]).decode("utf-8")

    try:
        if check_user > 0:
            authUsername = request.authorization["username"]
            authPassword = request.authorization["password"]

            if not any(authUsername and authPassword):
                return jsonify("Missing Username or Password"), 403

            response = coll_user.find_one({"username": authUsername})

            if response:
                if bcrypt.check_password_hash(response["password"], authPassword):
                    if coll_user.count_documents({"username": username_}) == 1:
                        return jsonify("Username already taken"), 409
                    coll_user.insert_one({"username": username_, "password": password_})

                    return jsonify(username_ + " added")
            else:
                return jsonify("Wrong password or username"), 403

        else:
            coll_user.insert_one({"username": username_, "password": password_})
            return jsonify(
                "This is the first user and needs no authorization to create: "
                + username_
                + " added"
            )
    except:
        return jsonify("Missing authentication"), 401


@app.route("/measurements", methods=["GET"])
def finding():
    date_ins = request.args["date"]
    if not date_ins:
        return jsonify("Need to add ?date=")
    collection = coll.find({"Date": date_ins}).sort("Time", -1)
    response = []
    for x in collection:
        response.append(x)
    return dumps(response)


@app.route("/measurements", methods=["POST"])
def inserting():
    username = request.authorization["username"]
    password = request.authorization["password"]

    if not any(username or password):
        return jsonify("This function is protected"), 403

    response = coll_user.find_one({"username": username})

    if response:
        if bcrypt.check_password_hash(response["password"], password):
            dt_swe = datetime.datetime.now(tz=pytz.timezone("Europe/Stockholm"))
            coll.insert_one(
                {
                    "Temperature": request.json["Temp"],
                    "Humidity": request.json["Hum"],
                    "Pressure": request.json["Press"],
                    "CO2": request.json["CO2"],
                    "TVOC": request.json["TVOC"],
                    "Rain": request.json["Rain"],
                    "Wind": request.json["Wind"],
                    "Date": str(dt_swe.date()),
                    "Time": str(dt_swe.time()),  # XD lam
                }
            )
            return jsonify("Data sent to DB!")
        else:
            return jsonify("invalid username or password")
    else:
        return jsonify("invalid username or password")


@app.route("/user/measurements", methods=["GET"])
def user_finding():

    date_ins = request.args["date"]
    try_date = coll.count_documents({"Date": date_ins})
    if try_date == 0:
        return "<h3>No data found</h3>"

    else:
        collection = coll.find({"Date": date_ins}).sort("Time", -1)
        return render_template("user.html", coll=collection, date=date_ins)


@app.errorhandler(404)
def page_not_found(e):
    return "404, Page not found", 404


@app.errorhandler(400)
def bad_request(e):
    return "400, bad request", 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=69)
