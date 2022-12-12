from flask import Flask
from flask import render_template

app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello World!"


@app.route('/welcome')
def welcome():
    personalmessage = "Hello World"
    return render_template('welcome.html',message=personalmessage)

@app.route('/<bucchamma>')
def hello_name(bucchamma):
    return "Hello {}!".format(bucchamma)

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug="True")
