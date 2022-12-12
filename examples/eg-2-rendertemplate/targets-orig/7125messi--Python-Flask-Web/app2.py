import db
from flask import Flask,render_template,json,jsonify,request

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/map", methods=["GET"])
def air_map():
    if request.method == "GET":
        sql = '''
        SELECT * FROM geoCoordMap
        '''
        res = db.query_data(sql)

    citys = []
    # 这里需要先设置一个空数组，将sql返回的数据进行逐个存到这个数组里面，在将结果转化为json格式
    for r in res:
        city_map = {}
        city_map['name'] = r['name']
        city_map['map'] = r['map']
        city_map['value'] = r['value']
        citys.append(city_map)

    return jsonify(citys)



if __name__ == '__main__':
    app.run()
