#!/usr/bin/env python
import os, requests, json, ast
from flask import Flask, render_template, redirect, url_for, request, make_response
from flask_restful import Api
from flask_jwt_extended import JWTManager
from guppy import hpy

# Local
from api import UserService, StockService
from controllers.UserController import UserController
from settings import JWT_SECRET_KEY

# refactor into config.py file
VIEW_DIRECTORY = "./views"
TEMPLATE_FOLDER = os.path.abspath(VIEW_DIRECTORY + "/templates/")
STATIC_FOLDER = os.path.abspath(VIEW_DIRECTORY + "/static/")

# api urls
LOCAL_URL = 'http://localhost:5000'
API_LOGIN = '/login/submit'
API_REGISTER = '/registration'
API_WATCHLIST_ADD = "/watch/add"
API_WATCHLIST_REMOVE = "/watch/remove"
API_REFRESH = "/token/refresh"
API_LOGOUT = "/logout/access"
API_LOGOUT_REFRESH = "/logout/refresh"
API_STOCK_PURCHASE_SELL = "/stock/purchase"
API_STOCK = "/stock"
API_USER_INFO = "/user/info"
ACCESS_COOKIE = 'user_access'
REFRESH_COOKIE = 'user_refresh'
USER_COOKIE = 'user_info'

app = Flask(__name__, template_folder=TEMPLATE_FOLDER, static_folder=STATIC_FOLDER)

app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY
app.config["JWT_BLACKLIST_ENABLED"] = True
app.config["JWT_BLACKLIST_TOKEN_CHECKS"] = ["access", "refresh"]

blacklist = set()
jwt = JWTManager(app)
api = Api(app)

# guppy
h = hpy()
print(h.heap())

# called every time client tries to access a secure endpoint
@jwt.token_in_blacklist_loader
def check_if_token_in_blacklist(decrypted_token):
    jti = decrypted_token["jti"]
    return UserController.tokenIsBlacklisted(jti)


# User Service
api.add_resource(UserService.UserRegistration, API_REGISTER)
api.add_resource(UserService.UserLogin, API_LOGIN)
api.add_resource(UserService.UserLogoutAccess, API_LOGOUT)
api.add_resource(UserService.UserLogoutRefresh, API_LOGOUT_REFRESH)
api.add_resource(UserService.TokenRefresh, API_REFRESH)
api.add_resource(UserService.UserInfo, API_USER_INFO)
# Stock Service
api.add_resource(StockService.GetStock, API_STOCK)
api.add_resource(StockService.PurchaseAsset, API_STOCK_PURCHASE_SELL)
api.add_resource(StockService.WatchAsset, API_WATCHLIST_ADD)
api.add_resource(StockService.RemoveWatchedAsset, API_WATCHLIST_REMOVE)

def refresh_token(request):
    token = {'Authorization': 'Bearer ' + request.cookies.get(REFRESH_COOKIE) }
    response = requests.post(LOCAL_URL + API_REFRESH, headers=token)
    return response.json()

def isLoggedIn(template, request):
    access = request.cookies.get(ACCESS_COOKIE)
    refresh = request.cookies.get(REFRESH_COOKIE)
    if access:
        return render_template(template)
    elif refresh:
        json_response = refresh_token(request)
        response = make_response(render_template(template))
        response.set_cookie(ACCESS_COOKIE, json_response.get("access_token"), max_age=900)
        return response

    return redirect(url_for('login'))

def get_header(request):
    try:
        access_token = request.cookies.get(ACCESS_COOKIE)
        if not access_token:
            refreshed = refresh_token(request)
            access_token = refreshed.get('access_token')
    except:
        return None;

    return {'Authorization': 'Bearer ' + access_token}

def set_tokens_redirect(request, json_response, page, username):
    response = make_response(redirect(url_for(page)))
    response.set_cookie(USER_COOKIE, username)
    response.set_cookie(ACCESS_COOKIE, json_response.get("access_token"), max_age=900)
    response.set_cookie(REFRESH_COOKIE, json_response.get("refresh_token"))
    return response

@app.route("/")
@app.route("/home")
def index():
    response = requests.post(LOCAL_URL + API_STOCK, data={"stock_symbol": "AAPL"}, headers=get_header(request))
    return isLoggedIn("index.html.j2", request) #, data=response.json())

@app.route("/market")
def market():
    return isLoggedIn("market/market.html.j2", request)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        response = requests.post(LOCAL_URL + API_LOGIN, data=request.form)
        json_response = response.json()

        if json_response.get("access_token"):
            return set_tokens_redirect(request, json_response, "index", request.form["username"])

        return render_template("login/login.html.j2", error=json_response.get("message"))

    return render_template("login/login.html.j2")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == 'POST':
        data = dict(request.form)
        # don't need field
        del data['password-repeat']
        response = requests.post(LOCAL_URL + API_REGISTER, data=data)
        json_response = response.json()

        if json_response.get("access_token"):
            return set_tokens_redirect(request, json_response, "index", request.form["username"])

        return render_template("login/register.html.j2", error=json_response.get("message"))

    return render_template("login/register.html.j2")

@app.route("/logout")
def logout():
    header = get_header(request)
    requests.post(LOCAL_URL + API_LOGOUT, headers=header)
    requests.post(LOCAL_URL + API_LOGOUT_REFRESH, headers=header)

    response = make_response(redirect(url_for('login')))
    response.delete_cookie(USER_COOKIE)
    response.delete_cookie(ACCESS_COOKIE)
    response.delete_cookie(REFRESH_COOKIE)
    return response

@app.route("/reset-password")
def reset_password():
    return isLoggedIn("login/password-reset.html.j2", request)

@app.route("/account")
def account():
    return isLoggedIn("account.html.j2", request)

@app.route("/stock/manage", methods=["GET", "POST"])
def manage_stock():
    if request.method == "POST":
        response = requests.post(LOCAL_URL + API_STOCK_PURCHASE_SELL, data=request.form, headers=get_header(request))
        json_response = response.json()
        # print(json_response)
        if json_response is not None:
        #     return render_template("stocks/sell.html.j2", error=json_response.get("message"))
        # elif json_response.get("data"):
            return render_template("stocks/sell.html.j2", data=json_response)

    return isLoggedIn("stocks/sell.html.j2", request)

def get_user_info(request):
    data = {"username" : request.cookies.get(USER_COOKIE)}
    response = requests.post(LOCAL_URL + API_USER_INFO, data=data, headers=get_header(request))
    return response.json()

# manage watch list + add / remove stock from watchlist
@app.route("/watchlist/manage")
def manage_watchlist():
    return isLoggedIn("watchlist/manage.html.j2", request)

@app.route("/watchlist/manage", methods=["POST"])
def remove_stock_watchlist():
    if request.method == "POST":
        user_info = get_user_info(request)
        user = {"user_id" : user_info["user_id"]}
        data = {**request.form, **user}
        response = requests.post(LOCAL_URL + API_WATCHLIST_REMOVE, data=data, headers=get_header(request))
        return render_template("watchlist/manage.html.j2", data=response.json())
    return render_template("watchlist/manage.html.j2")

@app.route("/watchlist/manage", methods=["POST"])
def add_stock_watchlist():
    if request.method == "POST":
        user_info = get_user_info(request)
        user = {"user_id" : user_info["user_id"]}
        data = {**request.form, **user}
        response = requests.post(LOCAL_URL + API_WATCHLIST_ADD, data=data, headers=get_header(request))
        return render_template("watchlist/manage.html.j2", data=response.json())
    return render_template("watchlist/manage.html.j2")


if __name__ == "__main__":
    app.run(host='0.0.0.0')    # Dockerized
    # app.run(debug=True)    # Debug
