import json
import os

from flask import Flask
from flask import send_from_directory
from flask import request
from flask import render_template
from pyecharts.charts import Bar, Pie, Line
from pyecharts import options as opts
from jinja2 import Markup

import db

app = Flask(__name__)

@app.route('/')
def hello_world():
    return hello_world2()

@app.route('/hello')
def hello_world2():
    data = "欢迎访问我的可视化作品"
    return render_template("welcome_here.html",data=data)

@app.route("/echarts")
def echarts():
    return render_template('echarts.html')


# 从MySQL查询结果数据
def get_data():
    sql = """
            select date,pv,uv from pvuv;
            """
    datas = db.query_data(sql)
    xdatas = [data['date'].strftime('%Y-%m-%d') for data in datas]
    ydatas = [data['pv'] for data in datas]
    return xdatas,ydatas

@app.route("/echarts2")
def echarts2():
    xdatas, ydatas = get_data()
    return render_template('echarts2.html',
                           xdatas=Markup(json.dumps(xdatas)),
                           ydatas=json.dumps(ydatas))

def get_data2():
    sql = """
            select sepal_length,sepal_width from iris_data;
            """
    datas = db.query_data(sql)
    datas = [(data['sepal_length'],data['sepal_width']) for data in datas]
    return datas

@app.route("/echarts3")
def echarts3():
    datas = get_data2()
    return render_template('echarts3.html',
                           datas=datas)


if __name__ == '__main__':
    app.run()
