from flask import render_template, json, url_for
from app import app
import os

@app.route('/')
@app.route('/index')
def index():
    
    return render_template('index.html', title='Home')

@app.route('/main')
def main():
    return 'Goodbye World'

@app.route('/pack')
def pack():

    jsonData = os.path.join(app.static_folder, 'multisltn2cycle.json')
    with open(jsonData) as data_file:
        data = json.load(data_file)

@app.route('/pick')
def pick():
    return render_template('Pick.html', title='Jarvis - Pick')

@app.route('/stow')
def stow():
    return render_template('Stow.html', title='Jarvis - Stow')

@app.route('/receive')
def receive():
    return render_template('Receive.html', title='Jarvis - Receive')



