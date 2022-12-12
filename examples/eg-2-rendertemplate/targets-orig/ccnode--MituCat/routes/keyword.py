from flask import render_template,jsonify,Blueprint,request,session,redirect,url_for,flash
from api.tools.front_dbtools import DB
from api.data_analysis.keyword_analysis import keyword_analysis
import time
from api.jd_spiders.crow_keyword import crow_keyword
import asyncio
import threading
keyword = Blueprint('keyword',__name__)
db = DB("mitucat")


#关键词分析页面跳转
@keyword.route("/keyword")
def k_analyze():
    if check_login()!=True:
        return redirect(url_for("user.login_page"))
    username = session["username"]
    return render_template("keyword/k_directory.html", username=username)


# 历史记录列表
@keyword.route("/k_directory",methods=["GET"])
def k_directory():
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
        res = db.query("select id,q_keyword,is_success,update_time from keyword_query_log "
                       "where user_id={0} and is_success=1 order by update_time desc limit {1},{2};".format(user_id,(page-1)*size,size))
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
            totaldata = db.query("select count(*) from keyword_query_log where user_id={} and is_success=1".format(user_id))
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
@keyword.route("/keyword",methods=["GET","POST"])
def getNewAnalys():
    if request.method == 'POST':
        try:
            keyword = request.form.get('keyword')
            user_id = session["user_id"]
            num = int(request.form.get('num'))
            if num > 5 or num < 1:
                return redirect(url_for('keyword.k_analyze'))
        # 生成查询记录
            sql = "insert into keyword_query_log(user_id,q_keyword) " \
                  "values({},'{}') ".format(user_id,keyword)
            q_id = db.commits(sql)[0][0]
        # #生成爬虫
            print("分析关键词{}".format(keyword))
            spider = crow_keyword(num,str(keyword),q_id)
            spider.coroutines()
            # 分析并将图片路径存入数据库
            keyword_analysis(q_id)
            path = '/static/source/user/{}/keyword/{}'.format(user_id, q_id)
            price_distribution = path + '/price_distribution.png'
            shop_ranking = path + '/shop_ranking.png'
            sql = "insert into keyword_analysis(q_id,price_distribution,shop_ranking) " \
                  "values({},'{}','{}')".format(q_id,price_distribution,shop_ranking)
            db.commit(sql)
            # 把记录变成成功
            sql = "update keyword_query_log set is_success=1 where id={}".format(q_id)
            db.commit(sql)
            username = session["username"]
            print("成功")
            return render_template("keyword/k_article.html", q_id=q_id, username=username)

        except Exception as e:
            print(e)
            flash("分析失败，链接格式不正确！","err")
            return redirect(url_for('keyword.k_analyze'))
    return redirect(url_for('keyword.k_analyze'))



# 具体历史记录页面跳转
@keyword.route("/k_history/<int:q_id>",methods=["GET"])
def k_history(q_id):
    if check_login()!=True:
        return redirect(url_for("user.login_page"))
    username = session["username"]

    return render_template("keyword/k_article.html", q_id=q_id, username=username)

# 获取图片链接
@keyword.route("/getKeywordResult",methods=["GET"])
def getKeywordResult():
    try:
        q_id =request.args.get('q_id')
        sql = "select price_distribution,shop_ranking from keyword_analysis where q_id={}".format(q_id)
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


# 检验登录
def check_login():
    try:
        session["username"]
        return True
    except:
        print("未登录")
        return False