from flask import render_template
import app
#导入表单处理方法
from . import bp_doctor
from .form import LoginForm

#前面的就不列举出来了，接着前面的写就可以了
#.......


@bp_doctor.route('/login')
def login():
    #创建一个表单实例
    form = LoginForm()
    return render_template('login.html',title='登 录',form=form)
