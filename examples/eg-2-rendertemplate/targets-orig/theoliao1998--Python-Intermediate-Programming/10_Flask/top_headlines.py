from flask import Flask, render_template
import requests
import json
from secret import API_KEY

# your code goes here

app = Flask(__name__)
baseurl = "https://newsapi.org/v2/top-headlines"
categories = {"business","entertainment","general","health","science","sports","technology"}

def topnews(topic):
    params = {"apiKey":API_KEY, "pagesize":5}

    if topic in categories:
        params["category"] = topic
    else:
        params["q"] = topic

    return [{"title":article["title"],"url":article["url"]} for article in json.loads(requests.get(baseurl,params).text)["articles"]]

@app.route('/newsfor/<user_name>')
def newsfor(user_name):
    return render_template('template.html', name=user_name.capitalize(), category="technology", news=topnews("technology"))

# ec1
@app.route('/news/<topic>')
def newstopic(topic):
    return render_template('template.html', category=topic, news=topnews(topic))

if __name__ == '__main__':  
    print('starting Flask app', app.name)  
    app.run(debug=True)
