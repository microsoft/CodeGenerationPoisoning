from flask import Flask, escape, request, render_template,redirect, url_for
import json

from sorting import Sorting

app = Flask(__name__)

class Application():

    def __init__(self, data):
        self._data = data

    @app.route('/')
    def index():
        return render_template('base.html')
    
    @app.route('/sorting', methods=['GET', 'POST'])
    def sorting_page():
        if request.method == 'POST':
            import numpy as np
            numbers = np.random.randint(1, 1001, 500)                
            sorting = Sorting(numbers, request.form['algorithm'])
            dictionary = sorting.__repr__()
            return render_template('sorting.html', obj=dictionary)
        return render_template('sorting.html')

    @app.route('/pathfinding')
    def pathfinding():
        return render_template('pathfinding.html')

if __name__ == '__main__':
    app.run('localhost', debug=True)