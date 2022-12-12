from flask import Flask
from flask import render_template
from flask import request

# 初始化Flask对象，用当前运行模块名作为参数
app = Flask(__name__)

# 路由参数指定访问url路径，url指定hello world函数
@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route('/hello')
def hello_world2():
    return 'Hello World2!'

@app.route('/html')
def hello_world3():
    data = "hello data" # 获取数据
    return render_template('hello.html',data = data) # 数据通过变量传递给模板，模板中通过{{data}}

# http://127.0.0.1:5000/user/user1
@app.route('/user/<username>',methods=['GET','POST'])
def get_user(username):
    return "hello {}".format(username)


# http://127.0.0.1:5000/data?a=a11&b=b11
# 可以用于查看某个用户和文章的信息
@app.route('/data',methods = ['GET','POST'])
def test_data():
    # URL查询参数
    # print(request.args)
    # print(request.args.get("a"),request.args.get("b"))
    # print(request.headers)
    # print(request.headers.get("User-Agent"))

    # JSON数据
    # print(request.data)
    # import json
    # print(json.loads(request.data))

    # request.cookies
    # print(request.cookies)
    # print(request.cookies.get("token"))

    # FORM表单参数
    print(request.form)
    print(request.form.get("username"),request.form.get("password"))

    return 'success'

if __name__ == '__main__':
    app.run()
