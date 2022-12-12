from flask import render_template, redirect, url_for, request
from application import app, db, bcrypt
from application.models import Robots, Algorithms, Users, Results
from application.forms import RobotForm, AlgorithmForm, RegistrationForm, LoginForm, ResultForm, UpdateRobotForm, UpdateAlgorithmForm
from flask_login import login_user, current_user,logout_user, login_required

@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html',title='Home')

@app.route('/robots')
def robot():
    robotData = Robots.query.all()
    return render_template('robot.html',title='Robot',robots=robotData)

@app.route('/algorithms')
def algorithm():
    algorithmData = Algorithms.query.all()
    return render_template('algorithm.html',title='Algorithm',algorithms=algorithmData)

@app.route('/results')
def result():
    resultData = Results.query.all()
    return render_template('result.html',title='Results',results=resultData)

@app.route('/add_result',methods=['GET','POST'])
@login_required
def addResult():
    form = ResultForm()
    if form.validate_on_submit():
        resultData = Results(
            robot_id = form.robot_id.data,
            algorithm_id = form.algorithm_id.data,
            time_taken = form.time_taken.data,
            author = current_user
       )

        db.session.add(resultData)
        db.session.commit()
        
        return redirect(url_for('result'))
    
    else:
        return render_template('add_result.html',title='Add result',form=form)        

@app.route('/add_algorithm', methods=['GET','POST'])
@login_required
def addAlgorithm():
    form = AlgorithmForm()
    if form.validate_on_submit():
        algorithmData = Algorithms(
            algorithm_name = form.algorithm_name.data,
            movement_type = form.movement_type.data
        )
        
        db.session.add(algorithmData)
        db.session.commit()

        return redirect(url_for('algorithm'))
    else:
        print(form.errors)
    return render_template('add_algorithm.html', title='Add Algorithm', form=form)


@app.route('/update_algorithm/<int:algorithm_id>',methods=['GET', 'POST'])
@login_required
def updateAlgorithm(algorithm_id):
    form = UpdateAlgorithmForm()
    currentAlgorithm = Algorithms.query.filter_by(id=algorithm_id).first()
    if form.validate_on_submit():
        currentAlgorithm.algorithm_name = form.algorithm_name.data,
        currentAlgorithm.movement_type = form.movement_type.data

        db.session.commit()

        return redirect(url_for('algorithm'))

    elif request.method == 'GET':
        form.algorithm_name.data = currentAlgorithm.algorithm_name,
        form.movement_type.data = currentAlgorithm.movement_type

    return render_template('update_algorithm.html', title='Update Algorithm', form=form, AlgorithmID=currentAlgorithm.id)    

@app.route('/add_robot', methods=['GET','POST'])
@login_required
def addRobot():
    form = RobotForm()
    if form.validate_on_submit():
        robotData = Robots(
            model_name = form.model_name.data,
            drive_type = form.drive_type.data,
            height = form.height.data,
            width = form.width.data,
            length = form.length.data
        )

        db.session.add(robotData)
        db.session.commit()

        return redirect(url_for('robot'))

    else:
        print(form.errors)

    return render_template('add_robot.html', title='Add Robot', form=form)

@app.route('/update_robot/<int:robot_id>',methods=['GET', 'POST'])
@login_required
def updateRobot(robot_id):
    form = UpdateRobotForm()
    print(robot_id)
    robotModel = Robots.query.filter_by(id=robot_id).first()
    if form.validate_on_submit():
        robotModel.model_name = form.model_name.data,
        robotModel.drive_type = form.drive_type.data,
        robotModel.height = form.height.data,
        robotModel.width = form.width.data,
        robotModel.length = form.length.data
        
        db.session.commit()

        return redirect(url_for('robot'))

    elif request.method == 'GET':
        form.model_name.data = robotModel.model_name
        form.drive_type.data = robotModel.drive_type
        form.height.data = robotModel.height
        form.width.data = robotModel.width
        form.length.data = robotModel.length
        
    return render_template('update_robot.html', title='Update Robot', form=form, robotID=robotModel.id)

@app.route('/algorithm/delete/<int:algorithm_id>', methods=['GET','POST'])
@login_required
def deleteAlgorithm(algorithm_id):
    algorithm = Algorithms.query.filter_by(id=algorithm_id).first()
    count = Results.query.filter_by(algorithm_id=algorithm.id).count()
    for i in range(count):
        result = Results.query.filter_by(algorithm_id=algorithm.id).first()
        db.session.delete(result)
        db.session.commit()
    db.session.delete(algorithm)
    db.session.commit()

    return redirect(url_for('algorithm'))

@app.route('/robot/delete/<int:robot_id>', methods=['GET','POST'])
@login_required
def deleteRobot(robot_id):
    robot = Robots.query.filter_by(id=robot_id).first()
    count = Results.query.filter_by(robot_id=robot.id).count()
    for i in range(count):
        result = Results.query.filter_by(robot_id=robot.id).first()
        db.session.delete(result)
        db.session.commit()
    db.session.delete(robot)
    db.session.commit()

    return redirect(url_for('robot'))    

@app.route('/result/delete/<int:result_id>',methods=['GET','POST'])
@login_required
def deleteResult(result_id):
    result = Results.query.filter_by(id=result_id).first()
    db.session.delete(result)
    db.session.commit()
    return redirect(url_for('result'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hash_pw = bcrypt.generate_password_hash(form.password.data)

        user = Users(
            email=form.email.data, 
            password=hash_pw,
            first_name = form.first_name.data,
            last_name = form.last_name.data)
    
        db.session.add(user)
        db.session.commit()

        return redirect(url_for('register'))
    return render_template('register.html',title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user=Users.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password,form.password.data):
            login_user(user, remember=form.password.data)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for('login'))
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))
