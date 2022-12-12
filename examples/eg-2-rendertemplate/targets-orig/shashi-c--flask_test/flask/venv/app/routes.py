from flask import render_template
from app import app
from app.forms import LoginForm
from flask_login import current_user, login_user
from app.models import User
from app.models import Student
from app.models import StudentTable
from flask_login import logout_user
from flask_login import login_required
from flask import request, redirect, url_for, flash
from werkzeug.urls import url_parse
from app import db
from sqlalchemy import update
from app.forms import RegistrationForm
from app.forms import StudentForm
from app.forms import StudentSearchForm
from app.forms import AuthorizationForm

@app.route('/')
@app.route('/index')
@login_required
def index():
    return render_template('index.html', title='Home', user=current_user, student=current_user.student)

@app.route('/login', methods=['GET', 'POST'])
def login():

    form = LoginForm()
    print(current_user)
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        print(user.is_authorized)
        if  not user.is_authorized and user.admin == False:
            flash('Not Authorized!!')
            flash('Please contact admin')
            return render_template('login.html', title='Sign In', form=form)

        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(url_for('index'))
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        user.set_admin()
        user.request_authorization(act_year = form.active_year.data, full_name = form.full_name.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration request succesfull!') 
        flash('Please check your email for confirmation')
        flash('NOTE: Average time taken to authorize a user is 2 hours')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/authorize', methods=['GET', 'POST'])
@login_required
def authorize():
    if current_user.admin == False:
        return redirect(url_for('index'))
    search = AuthorizationForm(request.form)
    print(search)
    if request.method == 'POST':
        return authorize_user(search)
    print('render template')
    return render_template('authorize.html', form = search)

def authorize_user(search):
    print('authorize user')
    usernameQueryStr = search.data['username']
    print('username : ' + usernameQueryStr)
    user = db.session.query(User).filter(User.username == usernameQueryStr).first()
    if user:
        print(user.username)
        user.is_authorized = True
        print('authorization success')
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/add-details', methods=['GET', 'POST'])
@login_required
def add_details():
    user = User.query.get_or_404(current_user.id)
    if user.student:
        print('Student exist')
        form = StudentForm(request.form, obj=user.student)
    else:
        print('new student')
        form = StudentForm(request.form)

    if request.method == 'POST':
        student = Student(name = form.name.data,
                    email = form.email.data,
                    phone = form.phone.data,
                    perm_addr = form.perm_addr.data,

                    qualification = form.qualification.data,
                    passout = form.passout.data,
                    stream = form.stream.data,
                    college = form.college.data,

                    tenth_percent = form.tenth_percent.data,
                    plus2_percent = form.plus2_percent.data,
                    degree_percent = form.degree_percent.data,
                    n_backlogs = form.n_backlogs.data,

                    courses =form.courses.data,
                    skills = form.skills.data,

                    hobbies = form.hobbies.data)
        #print(student.name)
        if user.student:
            print("updating")
            user.student.name = form.name.data
            user.student.email = student.email
            user.student.phone = student.phone
            user.student.perm_addr = student.perm_addr
                    
            user.student.qualification = student.qualification
            user.student.passout = student.passout
            user.student.stream = student.stream
            user.student.college = student.college
                    
            user.student.tenth_percent = student.tenth_percent
            user.student.plus2_percent = student.plus2_percent
            user.student.degree_percent = student.degree_percent
            user.student.n_backlogs = student.n_backlogs
                    
            user.student.courses = student.courses
            user.student.skills = student.skills
            user.student.hobbies = student.hobbies
        else:
            print("Creating")
            student.user = user 
            db.session.add(student)

        db.session.commit()
        flash('**** Congratulations, your details have been added! ****')
        return redirect(url_for('index'))
    elif request.method == 'GET':
        return render_template('v2student-details.html', title='Add Details', form=form)


@app.route('/show-details', methods=['GET', 'POST'])
@login_required
def show_details():
    print(current_user.student)
    result = []
    if current_user.student is None:
        flash('Nothing to show, Add your details first!!')
        return render_template('index.html', title='Home', user=current_user, student=current_user.student)
    else:
        result.append(current_user.student)
        table = StudentTable(result)
        table.border = True
        return render_template('show-details.html', title='Your Details', table=table)

'''
# TODO: Remove this method later
@app.route('/show-all', methods=['GET', 'POST'])
@login_required
def show_all():
    if current_user.admin == False:
        return redirect(url_for('index'))
    students = []
    users = User.query.all()
    for u in users:
        if u.admin == False:
            students.append(u.student)

    for s in students:
        print(s.name, s.email)
    return render_template('show-all.html', students=students)
'''

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search_student():
    if current_user.admin == False:
        return redirect(url_for('index'))
    search = StudentSearchForm(request.form)
    print(search)
    if request.method == 'POST':
        return search_results(search)
    print('render template')
    return render_template('search.html', form = search)

@app.route('/results')
@login_required
def search_results(search):
    print('searching !!! ')
    if current_user.admin == False:
        return redirect(url_for('index'))
    results = []

    qry=db.session.query(Student)

    personalQueryStr = search.data['personal']
    if personalQueryStr:
        if search.data['personalChoice'] == 'name':
            qry = db.session.query(Student).filter(Student.name == personalQueryStr)
        elif search.data['personalChoice'] == 'email':
            qry = db.session.query(Student).filter(Student.email == personalQueryStr)
        elif search.data['personalChoice'] == 'phone':
            qry = db.session.query(Student).filter(Student.phone == personalQueryStr)
        elif search.data['personalChoice'] == 'address': # TODO: WhooshAlchemy
            qry = db.session.query(Student).filter(Student.perm_addr == personalQueryStr)


    academicQueryStr = search.data['academic']
    if academicQueryStr:
        if search.data['academicChoice'] == 'qualification':
            if not qry.all() and not personalQueryStr:
                qry = db.session.query(Student).filter(Student.qualification == academicQueryStr)
            else:
                qry = qry.filter(Student.qualification == academicQueryStr)
        if search.data['academicChoice'] == 'passout':
            if not qry.all() and not personalQueryStr:
                qry = db.session.query(Student).filter(Student.passout == academicQueryStr)
            else:
                qry = qry.filter(Student.passout == academicQueryStr)
        if search.data['academicChoice'] == 'stream':
            if not qry.all() and not personalQueryStr:
                qry = db.session.query(Student).filter(Student.stream == academicQueryStr)
            else:
                qry = qry.filter(Student.stream == academicQueryStr)
        if search.data['academicChoice'] == 'college':
            if not qry.all() and not personalQueryStr:
                qry = db.session.query(Student).filter(Student.college == academicQueryStr)
            else:
                qry = qry.filter(Student.college == academicQueryStr)


    gradeQueryStr = search.data['grade']
    if gradeQueryStr:
        if search.data['gradeChoice'] == 'degree_percent':
            if not qry.all() and not personalQueryStr and not academicQueryStr:
                qry = db.session.query(Student).filter(Student.degree_percent >= float(gradeQueryStr))
            else:
                qry = qry.filter(Student.degree_percent >= float(gradeQueryStr))
        if search.data['gradeChoice'] == 'n_backlogs':
            if not qry.all() and not personalQueryStr and not academicQueryStr:
                qry = db.session.query(Student).filter(Student.n_backlogs <= int(gradeQueryStr))
            else:
                qry = qry.filter(Student.n_backlogs <= int(gradeQueryStr))

    courseQueryStr = search.data['courses']
    if courseQueryStr:
        if not qry.all() and not personalQueryStr and not academicQueryStr and not gradeQueryStr:
            qry = db.session.query(Student).filter(Student.courses == courseQueryStr)
        else:
            qry = qry.filter(Student.courses == courseQueryStr)

    skillQueryStr = search.data['skills']
    if skillQueryStr:
        if not qry.all() and not personalQueryStr and not academicQueryStr and not gradeQueryStr and not courseQueryStr:
            qry = db.session.query(Student).filter(Student.skills == skillQueryStr)
        else:
            qry = qry.filter(Student.skills == skillQueryStr)

    for item in qry.all():
        results.append(item)
    print(results)
    table = StudentTable(results)
    table.border = True
    return render_template('results.html', table=table)
