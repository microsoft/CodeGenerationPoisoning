from flask import Flask, request, render_template
import requests
from requests import get
import json
import time
from passwords import RandomOrgKey

app = Flask(__name__)


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/metrics')
def metrics():
    page = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Home</title>
</head>
<body style="background-color:black;color:white;">
<a href="../">Home</a><br>"""
    with open("requests.log", "r") as file:
        content = file.readlines()
        for line in content:
            dic = json.loads(line)
            page += "{<br>"
            page += "url:" + dic['url'] + "<br>"
            page += "metoda:" + dic['metoda'] + "<br>"
            page += "response:" + dic['response'] + "<br>"
            page += "latency:" + dic['latency'] + "<br>"
            page += "}<br>"
    page += """<script src="{{ url_for('static',filename='js/index.js') }}"></script>
</body>
</html>
    """
    return page


@app.route('/Request')
def Request():
    rates = getCurrencyExchange()
    print(rates)
    if rates is None:
        response = "IP reserved"
    else:
        response = "<h1>" + rates[0] + " " + rates[1] + "</h1><br>"
        for i in rates[2]:
            response += i + ":" + str(rates[2][i]) + "<br>"
    return response


def getCurrencyExchange():
    url1 = 'https://api.random.org/json-rpc/1/invoke'
    url2 = 'https://ipapi.co/'
    url3 = 'https://api.exchangerate-api.com/v4/latest/'
    log_file = open('requests.log', 'a')
    data = {
        'jsonrpc': '2.0',
        'method': 'generateIntegers',
        'params': {'apiKey': RandomOrgKey, 'n': 4, 'min': 1, 'max': 255, 'replacement': 'true', 'base': 10},
        'id': 24565
    }

    start_time = time.time() * 1000
    params = json.dumps(data)
    response = requests.post(url1, params)
    duration = time.time() * 1000 - start_time

    log = {'url': url1,
           'metoda': "POST",
           'response': response.text,
           'latency': str(int(duration))}

    log_file.write(json.dumps(log) + "\n")

    d = json.loads(response.text)

    st = ''
    for i in d['result']['random']['data']:
        st += '' + str(i) + '.'
    st = st[:-1]

    start_time = time.time() * 1000
    response = requests.get(url2 + st + "/json/")
    duration = time.time() * 1000 - start_time
    log = {'url': url2,
           'metoda': "GET",
           'response': response.text,
           'latency': str(int(duration))}

    log_file.write(json.dumps(log) + "\n")

    if response.status_code != 200:
        return None
    content = json.loads(response.text)
    if 'currency' in content.keys():
        currency = content['currency']
    else:
        return None
    start_time = time.time() * 1000
    response = requests.get(url3 + currency)
    duration = time.time() * 1000 - start_time
    log = {'url': url3,
           'metoda': "GET",
           'response': response.text,
           'latency': str(int(duration))}

    log_file.write(json.dumps(log) + "\n")

    if response.status_code != 200:
        return None
    log_file.close()
    return st, currency, json.loads(response.text)['rates']


if __name__ == '__main__':
    app.run()
