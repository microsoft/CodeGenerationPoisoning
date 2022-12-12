# _*_ coding: utf-8 _*_
from . import home
from app import db
from app.home.forms import LoginForm,RegisterForm,SuggetionForm
from app.models import User ,Area,Scenic,Travels,Collect,Suggestion,Userlog
from flask import render_template, url_for, redirect, flash, session, request
from werkzeug.security import generate_password_hash
from sqlalchemy import and_
from functools import wraps

def user_login(f):
    """
    登录装饰器
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("home.login"))
        return f(*args, **kwargs)

    return decorated_function

@home.route("/login/", methods=["GET", "POST"])
def login():
    """
    登录
    """
    form = LoginForm()              # 实例化LoginForm类
    if form.validate_on_submit():   # 如果提交
        data = form.data            # 接收表单数据
        # 判断用户名和密码是否匹配
        user = User.query.filter_by(email=data["email"]).first()    # 获取用户信息
        if not user :
            flash("Email does not exist！", "err")           # 输出错误信息
            return redirect(url_for("home.login")) # 调回登录页
        if not user.check_pwd(data["pwd"]):     # 调用check_pwd()方法，检测用户名密码是否匹配
            flash("Wrong Password！", "err")           # 输出错误信息
            return redirect(url_for("home.login")) # 调回登录页

        session["user_id"] = user.id                # 将user_id写入session, 后面用户判断用户是否登录
        # 将用户登录信息写入Userlog表
        userlog = Userlog(
            user_id=user.id,
            ip=request.remote_addr
        )
        db.session.add(userlog) # 存入数据
        db.session.commit()     # 提交数据
        return redirect(url_for("home.index")) # 登录成功，跳转到首页
    return render_template("home/login.html", form=form) # 渲染登录页面模板

@home.route("/register/", methods=["GET", "POST"])
def register():
    """
    注册功能
    """
    form = RegisterForm()           # 导入注册表单
    if form.validate_on_submit():   # 提交注册表单
        data = form.data            # 接收表单数据
        # 为User类属性赋值
        user = User(
            username = data["username"],            # 用户名
            email = data["email"],                  # 邮箱
            pwd = generate_password_hash(data["pwd"]),# 对密码加密
        )
        db.session.add(user) # 添加数据
        db.session.commit()  # 提交数据
        flash("register success！", "ok") # 使用flask存储成功信息
    return render_template("home/register.html", form=form) # 渲染模板

@home.route("/logout/")
def logout():
    """
    退出登录
    """
    # 重定向到home模块下的登录。
    session.pop("user_id", None)
    return redirect(url_for('home.login'))    


@home.route("/")
def index():
    """
    首页
    """
    area = Area.query.all() # 获取所有chapter
    hot_area = Area.query.filter_by(is_recommended = 1).limit(2).all() # 获取热门chapter
    scenic = Scenic.query.filter_by(is_hot = 1).all() # 热门Subsection
    return render_template('home/index.html',area=area,hot_area=hot_area,scenic=scenic) # 渲染模板

@home.route("/info/<int:id>/")
def info(id=None):  # id 为SubsectionID
    """
    详情页
    """
    scenic = Scenic.query.get_or_404(int(id)) # 根据SubsectionID获取Subsection数据，如果不存在返回404
    user_id = session.get('user_id',None)    # 获取用户ID,判断用户是否登录
    if user_id :                              # 如果已经登录
        count = Collect.query.filter_by(      # 根据用户ID和SubsectionID判断用户是否已经收藏该Subsection
            user_id =int(user_id),
            scenic_id=int(id)
        ).count()
    else :                                    # 用户未登录状态
        user_id = 0
        count = 0    
    return render_template('home/info.html',scenic=scenic,user_id=user_id,count=count)   # 渲染模板

@home.route("/collect_add/")
@user_login
def collect_add():
    """
    收藏Subsection
    """
    scenic_id = request.args.get("scenic_id", "")  # 接收传递的参数scenic_id
    user_id   = session['user_id']                  # 获取当前用户的ID
    collect = Collect.query.filter_by(              # 根据用户ID和SubsectionID判断是否该收藏
        user_id =int(user_id),
        scenic_id=int(scenic_id)
    ).count()
    # 已收藏
    if collect == 1:
        data = dict(ok=0)     # 写入字典
    # 未收藏进行收藏
    if collect == 0:
        collect = Collect(
            user_id =int(user_id),
            scenic_id=int(scenic_id)
        )
        db.session.add(collect)  # 添加数据
        db.session.commit()      # 提交数据
        data = dict(ok=1)        # 写入字典
    import json                 # 导入模块
    return json.dumps(data)     # 返回json数据

@home.route("/collect_cancel/")
@user_login
def collect_cancel():
    """
    收藏Subsection
    """
    id = request.args.get("id", "")    # 获取SubsectionID
    user_id = session["user_id"]       # 获取当前用户ID
    collect = Collect.query.filter_by(id=id,user_id=user_id).first() # 查找Collect表，查看记录是否存在
    if collect :                      # 如果存在
        db.session.delete(collect)     # 删除数据
        db.session.commit()             # 提交数据
        data = dict(ok=1)               # 写入字典
    else :
        data = dict(ok=-1)           # 写入字典
    import json                     # 引入json模块
    return json.dumps(data)         # 输出json格式


@home.route("/collect_list/")
@user_login
def collect_list():
    page = request.args.get('page', 1, type=int) # 获取page参数值
    # 根据user_id删选Collect表数据
    page_data = Collect.query.filter_by(user_id = session['user_id']).order_by(
        Collect.addtime.desc()
    ).paginate(page=page, per_page=3)                                     # 使用分页方法
    return render_template('home/collect_list.html',page_data=page_data) # 渲染模板

@home.route("/travels/<int:id>/")
def travels(id=None):
    """
    详情页
    """
    travels = Travels.query.get_or_404(int(id))
    return render_template('home/notes.html', travels=travels)

@home.route("/search/")
def search():
    """
    搜素功能
    """
    page = request.args.get('page', 1, type=int) # 获取page参数值 
    area = Area.query.all()    # 获取所有chapter
    area_id = request.args.get('area_id',type=int)  # Chapter
    star = request.args.get('star',type=int)        # 星级

    if area_id or star :    # 根据星级搜索Subsection
        filters = and_(Scenic.area_id==area_id,Scenic.star==star)
        page_data = Scenic.query.filter(filters).paginate(page=page, per_page=6)
    else :                  # 搜索全部Subsection
        page_data = Scenic.query.paginate(page=page, per_page=6)
    return render_template('home/search.html',page_data=page_data,area=area,area_id=area_id,star=star)
    
@home.route("/about/")
def about():
    """
    关于我们
    """
    return render_template('home/about.html')

@home.route("/contact/",methods=["GET", "POST"])
def contact():
    """
    联系我们
    """
    form = SuggetionForm()              # 实例化SuggestionForm类
    if form.validate_on_submit():       # 判断用户是否提交表单
        data = form.data                # 接收用户提交的数据
        # 为属性赋值
        suggestion = Suggestion(
            name = data["name"],
            email=data["email"],
            content = data["content"],
        )
        db.session.add(suggestion)       # 添加数据
        db.session.commit()              # 提交数据
        flash("Success！", "ok")        # 用flask存储发送成功消息
        form.content.data = ''           # 设置内容为空
    return render_template('home/contact.html',form=form) # 渲染模板，并传递表单数据