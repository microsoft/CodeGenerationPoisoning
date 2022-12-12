from flask import Flask
from flask import render_template
from flask import request

# 初始化Flask对象，用当前运行模块名作为参数
app = Flask(__name__)

# 路由参数指定访问url路径，url指定hello world函数
@app.route('/')
def hello_world():
    return 'Hello World!'

@app.route('/use_template')
def use_template():
    datas = [(1,"name1"),(2,"name2"),(3,"name3")]
    title = "学生信息"
    return render_template("use_template.html",datas = datas,title = title)

if __name__ == '__main__':
    app.run()
