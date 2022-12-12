from flask import render_template,jsonify,Blueprint,request,session,redirect,url_for,flash
from api.tools.front_dbtools import DB
from api.data_analysis.goods_analysis import goods_analysis
import time
from api.jd_spiders.crow_goods import crow_goods
import asyncio
import threading
import os
import sys
goods = Blueprint('goods',__name__)
db = DB("mitucat")


#商品分析页面跳转
@goods.route("/goods")
def g_analyze():
    if check_login()!=True:
        return redirect(url_for("user.login_page"))
    username = session["username"]
    return render_template("goods/g_directory.html", username=username)


# 历史记录列表
@goods.route("/g_directory",methods=["GET"])
def g_directory():
    if check_login() != True:
        return redirect(url_for("user.login_page"))
    user_id = session["user_id"]
    page = int(request.args.get('page'))
    size = int(request.args.get('size'))
    if page == None:
        page = 1
    if size == None:
        size = 10
    try :
        # 取出本页数据
        res = db.query("select id,q_url,is_success,update_time,q_name from goods_query_log "
                       "where user_id={0} and is_success=1 and is_del=0 order by update_time desc limit {1},{2};".format(user_id,(page-1)*size,size))
        if res == ():
            q_data = "None"
            totalPage = 0
        else:
            # 格式化时间
            q_data = list(res)
            for i in range(len(q_data)):
                q_data[i] = list(q_data[i])
                q_data[i][3] = q_data[i][3].strftime('%Y{y}%m{m}%d{d} %H{h}%M %p')\
                    .format(y='年',m='月',d='日',h=':')

            # 算出一共分几页
            totaldata = db.query("select count(*) from goods_query_log where user_id={} and is_success=1 and is_del=0".format(user_id))
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
        "data": q_data,
        "totalPage" : totalPage,
        "msg" : "查询成功",
        "status" : "200"

    }
    return jsonify(data)




# 新建商品分析
@goods.route("/goods",methods=["GET","POST"])
def getNewAnalys():
    if request.method == 'POST':
        #获取用户输入的url与评论页数
        url = str(request.form.get('url'))
        user_id = session["user_id"]
        num = int(request.form.get('num'))
        if num > 12 or num < 1:
            return redirect(url_for('goods.g_analyze'))
        # 生成查询记录
        try:
            sql = "insert into goods_query_log(user_id,q_url) " \
                  "values({},'{}') ".format(user_id,url)
            q_id = db.commits(sql)[0][0]
            #生成爬虫
            spider = crow_goods(url,num,q_id)
            goods_name = spider.coroutines()
            print("开始分析",q_id)
            # 分析并将图片路径存入数据库
            goods_analysis(q_id)
            path = '/static/source/user/{}/goods/{}'.format(user_id, q_id)
            sentiment = path + '/sentiment.png'
            daily_comment = path + '/daily_comment.png'
            wordcloud = path + '/wordcloud.png'
            sql = "insert into goods_analysis(q_id,sentiment_img,daily_comment,word_fq_img) " \
                  "values({},'{}','{}','{}')".format(q_id,sentiment,daily_comment,wordcloud)
            db.commit(sql)

            # 把记录变成成功
            sql = "update goods_query_log set is_success=1,q_name='{}' where id={}".format(goods_name,q_id)
            db.commit(sql)
            username = session["username"]
            return render_template("goods/g_article.html", q_id=q_id, username=username)
        except Exception as e:
            print(e)
            flash("分析失败！{}".format(e),"err")

            return redirect(url_for('goods.g_analyze'))
    return  redirect(url_for('goods.g_analyze'))



# 具体历史记录页面跳转
@goods.route("/g_history/<int:q_id>",methods=["GET"])
def g_history(q_id):
    if check_login()!=True:
        return redirect(url_for("user.login_page"))
    username = session["username"]
    return render_template("goods/g_article.html", q_id=q_id, username=username)

# 获取图片链接
@goods.route("/getGoodsResult",methods=["GET"])
def getGoodsResult():
    try:
        q_id =request.args.get('q_id')
        sql = "select sentiment_img,daily_comment,word_fq_img from goods_analysis where q_id={}".format(q_id)
        res = db.query(sql)
        if res:
            data = {
                "data": res,
                "msg": "查询成功",
                "status": "200"}

            return jsonify(data)
    except Exception as e:
        data = {
            "msg": "查询失败",
            "status": "500"
        }
        return jsonify(data)
    return ""


# 检验登录
def check_login():
    try:
        session["username"]
        return True
    except:
        print("未登录")
        return False
