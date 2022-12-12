from flask import render_template,jsonify,Blueprint,request,session,redirect,url_for,flash
from api.tools.front_dbtools import DB
from api.data_analysis.goods_analysis import goods_analysis
import time
from api.jd_spiders.crow_goods import crow_goods
import asyncio
import threading
admin = Blueprint('admin',__name__)
db = DB("mitucat")



# 管理页面
@admin.route("/admin_page")
def admin_page():
    if check_login()!=True:
        return redirect(url_for("user.login_page"))
    try:
        is_admin = session["is_admin"]
        if is_admin==1:
            return render_template("admin/admin.html")
    except Exception as e:
        print("错误：{}".format(e))
    return render_template("admin/adminError.html")


# 加载公告编辑
@admin.route("/edit_rewards")
def edit_rewards():
    username = session["username"]
    res = db.query("select title,r_describe,content from reward order by update_time desc limit 1")
    title = res[0][0]
    describe = res[0][1]
    content = res[0][2]
    return render_template("admin/edit_rewards.html",username=username,title=title,describe=describe,content=content)

# 更新公告
@admin.route("/edit_rewards", methods=['GET', 'POST'])
def update_rewards():
    if request.method == 'POST':
        title = request.form.get("title")
        describe = request.form.get("describe")
        content = request.form.get("myEdit")
        #提交sql
        db.commit("insert into reward(title,r_describe,content) "
                  "values('"+title+"','"+describe+"','"+content+"');")
    return redirect(url_for("admin.edit_rewards"))

# 跳转公告页面
@admin.route("/getReward")
def getReward():
    res = db.query("select title,content from reward order by update_time desc limit 1")
    username = session["username"]
    title = res[0][0]
    content = res[0][1]
    return render_template("admin/rewards.html",title=title,content=content,username=username)

# 加载用户管理
@admin.route("/user_manage")
def user_manage():
    username = session["username"]
    return render_template("admin/user_manage.html",username=username)


# 加载用户列表
@admin.route("/user_directory",methods=["GET"])
def user_directory():
    if check_login() != True:
        return redirect(url_for("user.login_page"))
    page = int(request.args.get('page'))
    size = int(request.args.get('size'))
    if page == None:
        page = 1
    if size == None:
        size = 10

    try :
        # 取出本页数据
        res = db.query("select id,login_name,is_freeze,is_admin from user_info "
                       "where is_del=0 order by id desc limit {},{};".format((page-1)*size,size))
        if res == ():
            res = "None"
            totalPage = 0
        else:

            # 算出一共分几页
            totaldata = db.query("select count(*) from user_info where is_del=0")
            totalPage = (totaldata[0][0]+size-1)/size
            totalPage = int(totalPage)

    except Exception as e:
        print("sql错误！原因{}".format(e))
        data = {
            "msg" : "查询失败",
            "status" : "500"
        }
        return jsonify(data)
    data = {
        "data": res,
        "totalPage" : totalPage,
        "msg" : "查询成功",
        "status" : "200"

    }
    return jsonify(data)


# 用户冻结
@admin.route("/user_freeze",methods=["POST"])
def user_freeze():
    if request.method == 'POST':
        #验证登录
        if check_login() != True:
            return redirect(url_for("user.login_page"))
        try:
            uid = int(request.args.get('uid'))
            sql = "update user_info set is_freeze=1 where id={}".format(uid)
            db.commit(sql)
        except Exception as e:
            print("错误：{}".format(e))
    return ""

# 用户解冻
@admin.route("/user_unfreeze",methods=["POST"])
def user_unfreeze():
    if request.method=='POST':

        if check_login() != True:
            return redirect(url_for("user.login_page"))

        try:
            uid = int(request.args.get('uid'))
            sql = "update user_info set is_freeze=0 where id={}".format(uid)
            db.commit(sql)
        except Exception as e:
            print("错误：{}".format(e))
    return ""

#用户删除
@admin.route("/user_del",methods=["POST"])
def user_del():
    #验证登录
    if request.method=='POST':
        if check_login() != True:
            return redirect(url_for("user.login_page"))
        try:
            uid = int(request.args.get('uid'))
            sql = "update user_info set is_del=1 " \
                  "where id={}".format(uid)
            db.commit(sql)
        except Exception as e:
            print("错误：{}".format(e))
    return ""



# 检验登录
def check_login():
    try:
        session["username"]
        return True
    except:
        print("未登录")
        return False