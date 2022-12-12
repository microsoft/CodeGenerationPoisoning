from flask import Flask
from flask import render_template
from flask import request

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello World!'

@app.route('/pvuv')
def pvuv():
    # read file
    data = []
    with open('./data/pvuv.txt') as fo:
        linenum = 0
        for row in fo   :
            if linenum == 0:
                linenum += 1
                continue
            date,pv,uv = row.strip().split("\t")
            data.append((date,pv,uv))

    # return html
    return render_template("pvuv.html",data = data)

if __name__ == '__main__':
    app.run()
