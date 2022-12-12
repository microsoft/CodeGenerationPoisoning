# -*- coding: utf-8 -*-
#  @ Date   : 2022/3/31 17:11
#  @ Author : RichardLau_Cx
#  @ Project: Python_Web_Demo
#  @ File   : getting_started.py
#  @ IDE    : PyCharm


from flask import Flask, url_for, render_template, request, redirect, abort

app = Flask(__name__)

# 静态文件
with app.test_request_context():
    url_for('static', filename='static/style.css')


# 路由
# 构造 URL
@app.route('/hello/')
def hello_richard():
    return 'hello_richard!'
    # print(type(app))


# 变量规则
@app.route('/user/<username>')
def show_user_profile(username):
    return 'User %s' % username


@app.route('/post/<float:post_id>')
def show_post(post_id):
    return 'Post %f' % post_id


# 模板渲染
@app.route('/test1/')
@app.route('/test1/<name>')
def test1(name=None):
    return render_template('test1.html', name=name)


# HTTP 方法
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # do_the_login()
        pass

    else:
        # show_the_login_info()
        pass


# 访问请求数据
# 环境局部变量
with app.test_request_context('/test2', method='POST'):
    assert request.path == '/test2'
    assert request.method == 'POST'


# with app.request_context(environ=environ):
#     assert request.method == 'POST'


# 请求对象
@app.route('/login', methods=['POST', 'GET'])
def login1():
    error = None

    if request.method == 'POST':
        # if valid_login():
        pass


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        f = request.files['the_file']
        f.save()


@app.route('/test3')
def test3():
    return redirect(url_for('login2'))


@app.route('/login2')
def login2():
    abort(401)  # 401 意味着禁止访问
    # this_is_never_executed


if __name__ == '__main__':
    # 调试模式
    app.debug = True
    app.run(host='0.0.0.0')
