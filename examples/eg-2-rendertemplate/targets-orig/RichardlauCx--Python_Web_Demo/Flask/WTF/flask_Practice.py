# -*- coding: utf-8 -*-
#  @ Date   : 2019/5/20 13:14
#  @ Author : ©RichardLau_Cx
#  @ file   : Richard.py
#  @ IDE    : PyCharm

# 对于表单插件的练习
from flask import Flask, render_template
from flask_wtf import Form, FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

app = Flask(__name__)
# app.secret_key = "Jarvis"
app.config["SECRET_KEY"] = "hard to guess string"


class Marvel_Form(FlaskForm):
    question_1 = "请问你叫什么名字啦"
    question_2 = "What is your name"

    user = StringField(question_1, validators=[DataRequired()])
    # submit = SubmitField('Submit')


@app.route('/', methods=("GET", "POST"))
def login():
    form = Marvel_Form()  # 实例化漫威表单对象

    if form.validate_on_submit():
        print("Successful Submit!")
        print("登陆账户名为：" + form.user.data)

        # if form.date['user'] == 'Tony Stark':
        if form.user.data == '刘进福':

            # return "Welcome Tony Stark to Marvel Universe!"
            return "你就是传说中，风度翩翩气质非凡的那个老兵嘛!"

        elif form.user.data == '王燕生':
            # return "Authentication does not pass."
            return "你就是那个婀娜多姿，小巧玲珑的王美人嘛！"

        else:
            return "你就是传说中的计算机神手嘛！！！"

    return render_template('login.html', form=form)  # 模板渲染


if __name__ == '__main__':
    app.run()
