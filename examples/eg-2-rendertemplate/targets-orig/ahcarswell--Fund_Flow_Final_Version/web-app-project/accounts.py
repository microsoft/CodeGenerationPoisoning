from flask import Flask, request, render_template, jsonify, Blueprint
from firebase import firebase

firebase = firebase.FirebaseApplication("https://fundflow-team3.firebaseio.com/", None)
result = firebase.get("/fundflow-team3/Users", '')

accounts = Blueprint('accounts', __name__)

def user_info():
    return result

def get_user_list():
    user_list = []
    for k, v in result.items():
        if isinstance(v, dict):
            user_list.append(v["username"])

    return user_list



def get_email_list():
    email_list = []
    for k, v in result.items():
        if isinstance(v, dict):
            email_list.append(v["email"])

    return email_list



# Can change the route name
@accounts.route('/backend/create_account', methods=['GET', 'POST'])
def create_account():
    # Assuming the method is post
    # This gets the data sent over from an ajax call (if that's what's being used)
    data = request.get_json()
    user_list = get_user_list()
    #email_list = # get_email_list()

    # Dictionary values aren't set in stone. Need to change it to what values are sent over from frontend
    if data["password"] != data["passConf"]:

        # Could be render template depending on the front end
        return {"username": data["username"], "pass": data["pass"], "verified": False}
    # The username is already present in the DB
    elif data["username"] in user_list:
  
        # Could be render template depending on the front end
        return {"username": data["username"], "pass": data["pass"], "verified": False}

    elif data["email"] in email_list:
        return {"username": data["username"], "pass": data["pass"], "verified": False}
    else:
        data = {
            'name': data["name"],
            'username': data["username"],
            'password': data["pass"],
        }
        res = firebase.post('/fundflow-team3/Users', data)

        donations_set_up = {
            'name': data["name"],
            'username':  data["username"],
            'email': data["email"],
            'org_list': list([["None", 0]])
        }

        donations_result = firebase.post('/fundflow-team3/past_donations', donations_set_up)
        # Based on a route to a dashboard that is specific to the user
       # return render_template("dashboard.html", user_info=data["username"])
        return {"username": data["username"], "pass": data["pass"], "verified": True}


@accounts.route('/backend/login', methods=['GET', 'POST'])
def login():
    # Assuming the method is post
    # This gets the data sent over from an ajax call (if that's what's being used)
    data = request.get_json()
    user_list = get_user_list()

    if data["username"] not in user_list:
        return {"username": data["username"], "pass": data["pass"], "verified": False}

    for k, v in result.items():
        if isinstance(v, dict) and v["username"] == data["username"]:
            if v["password"] == data["pass"]:
                data = {"message" : "login successful"}
                return {"username": data["username"], "pass": data["pass"], "verified": True}
                #elif data["password"] == full_dict[data["username"]]:

        #return render_template("dashboard.html", user=data["username"])
        # Does full_dict check everything at once? #full dict gets all the users in our database
    else:
        return {"username": data["username"], "pass": data["pass"], "verified": False}


# test create_account("Andrea", "andi", "andi101", "andi101", "andrea@gmail.com")

