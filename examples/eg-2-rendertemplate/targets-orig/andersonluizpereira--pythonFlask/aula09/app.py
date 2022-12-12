from flask import Flask, render_template, request
import json
app = Flask(__name__, template_folder ='templates')

@app.route('/')
def index():
    x = 50
    y = 10
    query = request.args.to_dict()
    return render_template('modelo.html', x=x, y=y, query=query)

if __name__ == '__main__':
    app.run()