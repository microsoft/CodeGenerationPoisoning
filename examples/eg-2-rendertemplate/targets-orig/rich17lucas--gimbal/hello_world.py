"""Simple Flask web application"""
import datetime
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
@app.route('/index.html')
def index():
    """Renders the index page when called"""
    now = datetime.datetime.now()
    time_string = now.strftime("%Y-%m-%d %H:%M:%S")
    template_data = {
        'title': 'HELLO!',
        'time': time_string
    }
    return render_template('index.html', **template_data)


@app.route('/cakes')
def cakes():
    """Renders the cake page"""
    return render_template('cakes.html')

if __name__ == "__main__":
    app.run(debug=True, port=1080, host='0.0.0.0')
