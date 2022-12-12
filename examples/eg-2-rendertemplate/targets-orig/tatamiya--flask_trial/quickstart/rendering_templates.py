from flask import Flask, render_template


app = Flask(__name__)


@app.route('/hello/')
@app.route('/hello/<name>')
def hello(name=None):
    '''
    Flask searches /templates/ dir.
    hello.html must be in /templates/.
    '''
    return render_template('hello.html', name=name)
