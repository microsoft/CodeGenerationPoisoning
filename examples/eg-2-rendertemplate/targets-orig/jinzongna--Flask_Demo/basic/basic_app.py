from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)

bp = Blueprint('basic', __name__, template_folder='templates', static_folder='static', url_prefix='/basic')

# hello world代码
@bp.route('/')
def hello_world():
    return render_template("basic.html")

# 通过URL传递参数
@bp.route('/user/<name>')
def hello_user(name):
    return 'Hello {0}!'.format(name)

# 利用模版显示变量名
@bp.route('/city/<city_name>')
def welcome(city_name):
    return render_template('city.html', name=city_name)

# 表单传递参数，模版输出页面
@bp.route('form', methods=['GET', 'POST'])
def form():
    name = None
    if request.method == 'POST' and 'name' in request.form:
        name = request.form['name']
    return render_template('form.html', name=name)

# 添加CSS和javascript
@bp.route('/css_js')
def css_js():
    return render_template('css_js.html')

# 遍历列表
@bp.route('/go_through_list')
def go_through_list():
    heroes = ["李白", "露娜", "韩信", "阿轲"]
    return render_template('go_through_list.html', heroes=heroes)

# 遍历字典
@bp.route("/go_through_dict")
def go_through_dict():
    hero = {"名字": "李白", "属性": "刺客", "铭文": "百穿"}
    return render_template("go_through_dict.html", info=hero)

# 条件渲染
@bp.route("/condition/<hero>")
def condition(hero):
    return render_template("condition.html", hero=hero)

# 过滤器的本质就是函数，用来修改变量的显示，格式化，运算等
@bp.route('/filters')
def filters():
    return render_template('filters.html')

# 定义自己的过滤器 my_reverse 返转列表
# @bp.add_app_template_filter('my_reverse')
# def do_list_reverse(li):
#     li.reverse()
#     return li
