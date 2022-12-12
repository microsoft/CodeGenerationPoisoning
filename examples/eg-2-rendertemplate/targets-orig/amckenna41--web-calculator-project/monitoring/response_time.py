
# File for testing response time for each function microservice in web calculator #

#import Python modules
import random
from flask import Flask
from flask import request
import urllib.request
from flask import jsonify
from flask import render_template   #used for html templates
from flask_cors import CORS, cross_origin
import func_url as fu
import time
import requests     #used to calculate time elasped for request


app = Flask(__name__)

#implement CORS
CORS(app, support_credentials=True)

#initialise function url's from func_url file
addURL = fu.ADD_URL
multURL = fu.MULT_URL
divURL = fu.DIV_URL
modURL = fu.MOD_URL
powerURL = fu.POWER_URL
subURL = fu.SUB_URL

#server response time microservice
@app.route("/")
@cross_origin(supports_credentials=True)
def get_server_response_time_result():

        x_arg = '?x='
        y_arg = '&y='

        #get x and y header arguments
        x_string = request.args.get('x')
        y_string = request.args.get('y')
        operator = request.args.get('operator')

        #if no x, y or operator arguments are input then return default values
        if (x_string == None) or (y_string == None) or (operator == None):
                x = 0
                y = 0
                message = "Invalid URL Parameters"
                print("Invalid URL parameters")
                return jsonify({"Default Value1" : x, "Default Value2" : y, "Output" : message})

        #convert x and y string args to int
        x = int(x_string)
        y = int(y_string)

        #if operator is divide then calculate time in ms to get a response from div microservice

        if operator == '/':
            func_url = divURL + x_arg + x_string + y_arg + y_string
            value = urllib.request.urlopen(func_url).read()         #get response from div service
            response = requests.get(func_url)                       #calculate response time
            time = response.elapsed.total_seconds()                 #get toal response time in seconds
            total_time = time * 1000                                #convert seconds to ms
            time_string = str(total_time)                           #convert repsonse time to string

            #return elapsed time in ms
            return jsonify({"Value1" : x_string, "Value2" : y_string, "Time Elapsed in ms" : time_string})

        #if operator is multiply then calculate time in ms to get a response from mult microservice

        if operator == '*':
            func_url = multURL + x_arg + x_string + y_arg + y_string
            value = urllib.request.urlopen(func_url).read()         #get response from mult service
            response = requests.get(func_url)                       #calculate response time
            time = response.elapsed.total_seconds()                 #get toal response time in seconds
            total_time = time * 1000                                #convert seconds to ms
            time_string = str(total_time)                           #convert repsonse time to string

            #return elapsed time in ms
            return jsonify({"Value1" : x_string, "Value2" : y_string, "Time Elapsed in ms" : time_string})

        #if operator is add then calculate time in ms to get a response from add microservice

        if operator == '+':
            func_url = addURL + x_arg + x_string + y_arg + y_string
            value = urllib.request.urlopen(func_url).read()         #get response from add service
            response = requests.get(func_url)                       #calculate response time
            time = response.elapsed.total_seconds()                 #get toal response time in seconds
            total_time = time * 1000                                #convert seconds to ms
            time_string = str(total_time)                           #convert repsonse time to string

            #return elapsed time in ms
            return jsonify({"Value1" : x_string, "Value2" : y_string, "Time Elapsed in ms" : time_string})

        #if operator is subtract then calculate time in ms to get a response from sub microservice

        if operator == '-':
            func_url = subURL + x_arg + x_string + y_arg + y_string
            value = urllib.request.urlopen(func_url).read()         #get response from sub service
            response = requests.get(func_url)                       #calculate response time
            time = response.elapsed.total_seconds()                 #get toal response time in seconds
            total_time = time * 1000                                #convert seconds to ms
            time_string = str(total_time)                           #convert repsonse time to string

            #return elapsed time in ms
            return jsonify({"Value1" : x_string, "Value2" : y_string, "Time Elapsed in ms" : time_string})

        #if operator is power then calculate time in ms to get a response from power microservice

        if operator == '^':
            func_url = powerURL + x_arg + x_string + y_arg + y_string
            value = urllib.request.urlopen(func_url).read()         #get response from power service
            response = requests.get(func_url)                       #calculate response time
            time = response.elapsed.total_seconds()                 #get toal response time in seconds
            total_time = time * 1000                                #convert seconds to ms
            time_string = str(total_time)                           #convert repsonse time to string

            #return elapsed time in ms
            return jsonify({"Value1" : x_string, "Value2" : y_string, "Time Elapsed in ms" : time_string})

        #if operator is modulus then calculate time in ms to get a response from mod microservice

        if operator == '%':
            func_url = modURL + x_arg + x_string + y_arg + y_string
            value = urllib.request.urlopen(func_url).read()         #get response from mod service
            response = requests.get(func_url)                       #calculate response time
            time = response.elapsed.total_seconds()                 #get toal response time in seconds
            total_time = time * 1000                                #convert seconds to ms
            time_string = str(total_time)                           #convert repsonse time to string

            #return elapsed time in ms
            return jsonify({"Value1" : x, "Value2" : y, "Time Elapsed in ms" : time_string})

#** HTTP Error handling **#

#Error handling function for http error 400
@app.errorhandler(400)
def not_found(e):

    print(e)
    return render_template("400.html")

#Error handling function for http error 404
@app.errorhandler(404)
def not_found(e):

    print(e)
    return render_template("404.html")

#Error handling function for http error 502
@app.errorhandler(502)
def bad_gatway(error=None):

    print(e)
    return render_template("502.html")

#Error handling function for http error 503
@app.errorhandler(503)
def internal_error(e):

    print(e)
    return render_template("503.html")

#Error handling function for http error 504
@app.errorhandler(504)
def internal_error(e):

    print(e)
    return render_template("504.html")

#main function to call monitoring service on port 5000
if __name__ =='__main__':
    print('Starting service')
    app.run(host='0.0.0.0', port = 5000, debug = True)
