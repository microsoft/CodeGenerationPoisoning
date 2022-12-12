import db
from flask import Flask, request, render_template, jsonify

app = Flask(__name__)


@app.route('/')
def hello_world():
    return '欢迎学习异步数据加载'


@app.route("/weather", methods=["GET"])
def weather():
    if request.method == "GET":
        sql = '''
        SELECT * FROM weather
        '''
        res = db.query_data(sql)
    return jsonify(
        month=[x['month'] for x in res],
        evaporation=[x['evaporation'] for x in res],
        precipitation=[x['precipitation'] for x in res]
    )

@app.route('/map')
def map():
    return render_template('map.html')


if __name__ == "__main__":
    app.run()
