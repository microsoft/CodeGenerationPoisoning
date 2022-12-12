
#Main app for proxy router microservice for web calculator #

#import python modules and dependancies
from flask import Flask
from flask import request
from flask import jsonify
from flask_cors import CORS, cross_origin
import urllib.request
import func_url as fu
from urllib.request import urlopen
import json
from flask import render_template

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

#proxy server microservice function
@app.route("/")
@cross_origin(supports_credentials=True)
def proxy_router():

    #get argument parameters
    x_string = request.args.get('x')
    y_string = request.args.get('y')
    x_arg = '?x='
    y_arg = '&y='
    operator = request.args.get('operator')

    #default values for the x, y and operator variables
    default_x = 0
    default_y = 0
    default_operator = ""

    #if one of the parameters is missing set values to the default values
    if (x_string == "") or (y_string == "") or (operator == ""):
        return jsonify({"Parameter Values missing, setting to default values - X" : default_x, "Y": default_y, "answer" :default_operator})


    #if operator is divide then call divide url function
    if operator == '/':

        http_output = divURL + x_arg + x_string + y_arg + y_string
        url_output = urlopen(http_output)
        json_obj = url_output.read()
        json_data = json.loads(json_obj)
        result = json_data['Answer']
        #value = urllib.request.urlopen(http_output).read()
        return jsonify({"Value1" : x_string, "Value2" : y_string, "Answer" : result})

    #if operator is multiply then call multiply url function
    if operator == '*':

        http_output = multURL + x_arg + x_string + y_arg + y_string
        url_output = urlopen(http_output)
        json_obj = url_output.read()
        json_data = json.loads(json_obj)
        result = json_data['answer']
        #value = urllib.request.urlopen(http_output).read()
        return jsonify({"Value1" : x_string, "Value2" : y_string, "answer" : result})


    #if operator is power then call power url function
    if operator == '^':

        http_output = powerURL + x_arg + x_string + y_arg + y_string
        url_output = urlopen(http_output)
        json_obj = url_output.read()
        json_data = json.loads(json_obj)
        result = json_data['answer']
        #value = urllib.request.urlopen(http_output).read()
        return jsonify({"Value1" : x_string, "Value2" : y_string, "answer" : result})

    #if operator is modulus then call modulus url function
    if operator == '%':

        http_output = modURL + x_arg + x_string + y_arg + y_string
        #value = urllib.request.urlopen(http_output).read()
        url_output = urlopen(http_output)
        json_obj = url_output.read()
        json_data = json.loads(json_obj)
        result = json_data['answer']

        return jsonify({"Value1" : x_string, "Value2" : y_string, "answer" : result})


    #if operator is addition then call add url function
    if operator == '+':

        http_output = addURL + x_arg + x_string + y_arg + y_string
        #value = urllib.request.urlopen(http_output).read()
        url_output = urlopen(http_output)
        json_obj = url_output.read()
        json_data = json.loads(json_obj)
        result = json_data['answer']

        return jsonify({"Value1" : x_string, "Value2" : y_string, "answer" : result})

    #if operator is subtract then call sub url function
    if operator == '-':

        http_output = subURL + x_arg + x_string + y_arg + y_string
        #value = urllib.request.urlopen(http_output).read()
        url_output = urlopen(http_output)
        json_obj = url_output.read()
        json_data = json.loads(json_obj)
        result = json_data['answer']

        return jsonify({"Value1" : x_string, "Value2" : y_string, "answer" : result})


    #if operator not found output 404 error
    else:
        not_found()

#**HTTP Error handling**#

#Error handling function for http error 400
@app.errorhandler(400)
def not_found(error=None):

    return render_template("400.html")

#Error handling function for http error 404
@app.errorhandler(404)
def not_found(error=None):

    return render_template("404.html")

#Error handling function for http error 502
@app.errorhandler(502)
def bad_gatway(error=None):

    return render_template("502.html")

#Error handling function for http error 503
@app.errorhandler(503)
def internal_error(error=None):

    return render_template("503.html")

#Error handling function for http error 504
@app.errorhandler(504)
def internal_error(error=None):

    return render_template("504.html")

#main function to call proxy server on port 5000
if __name__ =='__main__':
    print('Starting service')
    app.run(host='0.0.0.0', port = 5000, debug = True)
