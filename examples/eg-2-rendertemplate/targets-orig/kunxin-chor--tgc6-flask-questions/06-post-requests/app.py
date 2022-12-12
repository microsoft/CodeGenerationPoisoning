from flask import Flask, render_template, request, redirect, url_for
import os

app = Flask(__name__)


# your code here!
@app.route("/")
def hello():
    return render_template("index.template.html")


@app.route("/", methods=['POST'])
def processHello():
    return render_template('process-hello.template.html')


# "magic code" -- boilerplate
if __name__ == '__main__':
    app.run(host=os.environ.get('IP'),
            port=int(os.environ.get('PORT')),
            debug=True)