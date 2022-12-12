from flask import Flask,render_template,session,redirect,url_for,request,flash
import os
from routes.goods import goods
from routes.user import user
from routes.keyword import keyword
from routes.admin import admin
import datetime
from api.tools.front_dbtools import DB
db = DB("mitucat")
import re
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

#添加其他蓝图到主体
app.register_blueprint(goods)
app.register_blueprint(user)
app.register_blueprint(keyword)
app.register_blueprint(admin)

def check_login():
    try:
        session["username"]
        return True
    except:
        print("未登录")
        return False

# 首页跳转
@app.route("/")
def index():
    if check_login()!=True:
        return redirect(url_for("user.login_page"))
    user_id = session["username"]
    res = db.query("select title,r_describe,update_time from reward order by update_time desc limit 1")
    title = res[0][0]
    describe = res[0][1]
    update_time = res[0][2]
    mouth = update_time.strftime('%m{m}').format(m='月')
    day = update_time.strftime('%d')
    update_time = update_time.strftime('%Y-%m-%d')
    return render_template("index.html",user_id=user_id,title=title,describe=describe
                           ,mouth=mouth,day=day,update_time=update_time)
    # return render_template("user/login.html")


#关键词分析
@app.route("/keyword")
def k_analyze():
    if check_login() != True:
        return redirect(url_for("user.login_page"))
    return render_template("keyword/k_directory.html")


if __name__ == "__main__":
    # debug=True
     app.run(
      host='127.0.0.1',
      port=5069,
      debug=True)