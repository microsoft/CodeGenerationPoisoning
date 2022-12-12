# This is flex server for our application
# It's gonna have the main routes, and will serve HTML
import logging

from flask import Flask, make_response, redirect
from flask import render_template
from flask import send_from_directory
from flask import request
from auth import google_auth_login
from datastore import insertClient
import datastore
from placeOrder import serveOrder
from placeOrder import processOrder


app = Flask(__name__, static_url_path='')


@app.route('/')
def index():
    """Return a friendly HTTP greeting."""
    if request.cookies.get('email') is None or request.cookies.get("email") == '':
        return redirect('/login')
    response = make_response(render_template('index.html'))
    response.set_cookie('lname', '')
    response.set_cookie('fname', '')
    return response


@app.route('/placeOrder')
def placeOrder():
    return serveOrder(request)

@app.route('/submitOrder',methods=['POST'])
def submitOrder():
    return processOrder(request)


@app.route('/login')
def login():
    if request.cookies.get('email') is not None and request.cookies.get("email") != '':
        return redirect('/')
    return render_template('login.html')


@app.route('/login/google')
def login_google():
    ok, user = google_auth_login()
    if ok:
        response = make_response(render_template('phone_registration.html'))
        response.set_cookie('lname', user[0])
        response.set_cookie('fname', user[1])
        response.set_cookie('email', user[2])
        return response
    else:
        return 'not ok'


@app.route('/phone')
def get_phone():
    phone_number = request.args.get('value')
    lname, fname, email = request.cookies.get('lname'), request.cookies.get('fname'), request.cookies.get('email')
    insertClient(lname, fname, email, phone_number)
    return redirect('/')


@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


@app.route('/orders')
def order():
    return render_template("orders.html")


@app.route('/getComenzi')
def getComenzi():
    comenzi = datastore.get_comenzi()
    return comenzi


@app.route('/work', methods=['POST'])
def work():
    if request.method == 'POST':
        data = list(request.form)[0]

        print(data)
        print(datastore.update_comenzi(data))
        return "asdasd"


if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='127.0.0.1', port=8081, debug=True)
# [END gae_flex_quickstart]
