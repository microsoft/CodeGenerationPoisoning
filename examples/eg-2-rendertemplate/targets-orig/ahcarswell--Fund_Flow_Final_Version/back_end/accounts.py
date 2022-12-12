from flask import Flask, request, render_template, jsonify
from firebase import firebase

firebase = firebase.FirebaseApplication("https://fundflow-team3.firebaseio.com/", None)
result = firebase.get("/fundflow-team3/Users", '')


def user_info():
    return result


def get_user_list():
    user_list = []
    for key in result:
        user_list.append(key["username"])
    return user_list


def get_email_list():
    email_list = []
    for key in result:
        email_list.append(key["email"])
    return email_list

# Can change the route name
@app.route('/backend/create_account', methods=['GET', 'POST'])
def create_account():
    # Assuming the method is post
    # This gets the data sent over from an ajax call (if that's what's being used)
    data = request.get_json()
    user_list = get_user_list()
    email_list = get_email_list()

    # Dictionary values aren't set in stone. Need to change it to what values are sent over from frontend
    if data["password"] != data["confirm_password"]:
        response = {
            "error": "The passwords do not match.",
            "success": False
        }
        # Could be render template depending on the front end
        return jsonify(response=response)
    # The username is already present in the DB
    elif data["username"] in user_list:
        response = {
            "error": "The username is already in use. Please choose a new one.",
            "success": False
        }
        # Could be render template depending on the front end
        return jsonify(response=response)

    elif data["email"] in email_list:
        response = {
            "error": "The email is already in use. Please enter a new one.",
            "success": False
        }
        return jsonify(response=response)
    else:
        data = {
            'name': data["name"],
            'username': data["username"],
            'password': data["password"],
            'email': data["email"]
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
        return render_template("dashboard.html", user_info=data["username"])


@app.route('/backend/login', methods=['GET', 'POST'])
def login():
    # Assuming the method is post
    # This gets the data sent over from an ajax call (if that's what's being used)
    data = request.get_json()
    user_list = get_user_list()

    if data["username"] not in user_list:
        response = {
            "error": "We do not have an account registered under that username",
            "success": False
        }
        return jsonify(response=response)
    elif data["password"] == full_dict[data["username"]]:
        return render_template("dashboard.html", user=data["username"])
        # Does full_dict check everything at once? #full dict gets all the users in our database
    else:
        response = {
            "error": "The password does not match the password in the system",
            "success": False
        }
        return jsonify(response=response)


# test create_account("Andrea", "andi", "andi101", "andi101", "andrea@gmail.com")

