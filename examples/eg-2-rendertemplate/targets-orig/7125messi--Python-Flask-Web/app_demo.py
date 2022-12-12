from flask import Flask
from flask import render_template

# 初始化Flask对象，用当前运行模块名作为参数
app = Flask(__name__)

# 路由参数指定访问url路径，url指定hello world函数
@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route('/hello')
def hello_world2():
    return 'Hello World2!'


# 不好使用，可以使用templates模板
# @app.route('/html')
# def hello_world3():
#     return """
#         <html>
#             <body>
#                 <h1 style = "color:#e00;">hello world!</h1>
#             </body>
#         </html>
#     """

# static可以直接访问
# http://127.0.0.1:5000/static/1.jpg
# 也可以放在html中

# 通过模板templates直接访问

@app.route('/html')
def hello_world3():
    data = "hello data" # 获取数据
    return render_template('hello.html',data = data) # 数据通过变量传递给模板，模板中通过{{data}}


if __name__ == '__main__':
    app.run()
