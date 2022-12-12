from flask import render_template, Flask
from datetime import datetime

app = Flask(__name__)

# Check for UUID --> https://www.jitsejan.com/python-and-javascript-in-flask.html #35bf5b
# Command + Shift + R --> reset the cache

@app.route('/')
def start():
    username = {"user":"NameDot"}
    return render_template("mirrur.html", title='Mirrur',time=datetime.year, \
           user=username)


if __name__ == '__main__':
    app.run()
