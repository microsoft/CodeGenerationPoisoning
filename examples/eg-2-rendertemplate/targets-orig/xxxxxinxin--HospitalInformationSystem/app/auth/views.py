from flask import render_template, redirect, flash, request, session, url_for
# 导入表单处理方法
from werkzeug.security import check_password_hash, generate_password_hash

from . import bp_auth
from ..model import Patient, MedicalStaff, Department, db
from .form import LoginForm


@bp_auth.route('/', methods=['GET', 'POST'])
def welcome():
    return render_template('welcome.html')
    # return "ok"


@bp_auth.route('/login', methods=['GET', 'POST'])
def login():
    # form = LoginForm()
    # #验证表格中的数据格式是否正确
    # if form.validate_on_submit():
    #     #闪现的信息会出现在页面，当然在页面上要设置
    #     flash('用户登录的名户名是:{} , 是否记住我:{}'.format(
    #         form.username.data,form.remember_me.data))
    #     #重定向至首页
    #     return redirect('/')
    # #首次登录/数据格式错误都会是在登录界面
    # return render_template('index.html', title='登录', form=form)
    if request.method == "POST":
        patientID = request.form["ID"]
        password = request.form["password"]
        error = None
        print(patientID)
        print(password)

        user = Patient.query.filter(Patient.patientID == patientID).first()


        if user is None:
            error = "Incorrect username."
            print("Incorrect username.")
        elif not check_password_hash(user.password, password):
            error = "Incorrect password."
            print("Incorrect password.")

        if error is None:
            # store the wechat id in a new session and return to the index
            session.clear()
            session["user_id"] = user.patientID
            # return render_template('wechat/index.html', alive=bot.alive, bot=bot)
            #
            #return redirect(url_for('patient.homepage()', userid=patientID))
            return "loginOK"


        flash(error)

    return render_template("index.html")


@bp_auth.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == "POST":
        error = None
        pName = request.form["name"]
        print(pName)
        password = request.form["password"]
        print(password)

        gender = request.form["gender"]
        print(gender)
        birthday = request.form["birthday"]
        print(birthday)
        phoneNumber = request.form["phonenumber"]

        print(phoneNumber)

        gender = 'm'

        if Patient.query.filter(Patient.phoneNumber == phoneNumber).first() is not None:
            error = "User {0} is already registered.".format(phoneNumber)

        # patientID = db.Column(db.CHAR(4), primary_key=True)  # 每个用户记得添加用户组
        # name = db.Column(db.CHAR(20))
        # gender = db.Column(db.CHAR(1))
        # birthDay = db.Column(db.DATE)
        # phoneNumber = db.Column(db.CHAR(11))
        # address = db.Column(db.CHAR(20))
        # password = db.Column(db.VARCHAR(100))
        if error is None:
            db.session.add(Patient(patientID='0001', phoneNumber=phoneNumber, password=generate_password_hash(password),
                           name=pName, gender=gender, birthDay=None))
            db.session.commit()
            redirect(url_for("auth.login"))
    return render_template('register.html')
