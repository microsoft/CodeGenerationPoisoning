from flask import render_template, redirect, url_for, request
from app import app, db, bcrypt
from flask_login import login_user, current_user, logout_user, login_required
from app.models import Users, Workout, Exercises, ExercisesInWorkout, Reviews
from app.forms import RegistrationForm, LoginForm, WorkoutForm, UpdateRepsForm, ReviewForm
from datetime import datetime

def add_exercises():
    userLevel =Users.query.filter_by(userid = current_user.userid).first().level
    currentWorkout = Workout.query.filter_by(userid= current_user.userid).order_by(Workout.workoutid.desc()).first()
    if userLevel > 2:
            exercise1 = Exercises.query.filter_by(exerciseid=userLevel-2).first()
            exercise2 = Exercises.query.filter_by(exerciseid=userLevel-1).first()
            exercise3 = Exercises.query.filter_by(exerciseid=userLevel).first()
            currentWorkout.workout.append(exercise1)
            currentWorkout.workout.append(exercise2)
            currentWorkout.workout.append(exercise3)
            db.session.commit()
    elif userLevel == 2:
            exercise1 = Exercises.query.filter_by(exerciseid=userLevel-1).first()
            exercise2 = Exercises.query.filter_by(exerciseid=userLevel).first()
            currentWorkout.workout.append(exercise1)
            currentWorkout.workout.append(exercise2)
            db.session.commit()
    elif userLevel ==1:
            exercise1 = Exercises.query.filter_by(exerciseid=userLevel).first()
            currentWorkout.workout.append(exercise1)

@app.route('/')
@app.route('/home/')
def home():
    reviewData = Reviews.query.order_by(Reviews.workoutid.desc()).all()
    return render_template('home.html', title= 'Home', reviews= reviewData)

@app.route('/about')
def about():
    return render_template('about.html', title= 'About')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        if form.level.data < 1:
            setLevel = 1
        elif form.level.data <5:
            setLevel = 2
        else:
            setLevel = 3
        hash_pw = bcrypt.generate_password_hash(form.password.data)
        user = Users(username=form.username.data, password= hash_pw, level= setLevel)
        
        
        
        db.session.add(user)
        
        db.session.commit()
        
        return redirect(url_for('login'))
    return render_template('register.html', title = 'Register', form=form)

@app.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('workout'))
    form = LoginForm()
    if form.validate_on_submit():
        user=Users.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember= form.remember.data)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for('workout'))
    return render_template('login.html', title = 'Login', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/coverage')
def coverage():
    return render_template('coverage.html')


@app.route('/workout', methods=['GET','POST'])
@login_required
def workout():
    userLevel =Users.query.filter_by(userid = current_user.userid).first().level
    currentWorkout = Workout.query.filter_by(userid= current_user.userid).order_by(Workout.workoutid.desc()).first()
    
    if not currentWorkout:
        Workout.create(Workout)
        add_exercises()
        return redirect(url_for('workout'))
    
    lastFinishedExercise = ExercisesInWorkout.query.filter_by(workoutid = currentWorkout.workoutid).order_by(ExercisesInWorkout.workoutid.desc()).first().reps_completed 
    
    if lastFinishedExercise > 0:
        Workout.create(Workout)
        add_exercises()
        return redirect(url_for('workout'))

    getExercises = ExercisesInWorkout.query.filter_by(workoutid = currentWorkout.workoutid).all()
    index =1
    for exercise in getExercises:
        if len(getExercises) == 3:
            if index == 1:
                exercise1 = exercise.exerciseid
                index += 1
                continue
            elif index ==2:
                exercise2 = exercise.exerciseid
                index +=1
                continue
            elif index ==3:
                exercise3 = exercise.exerciseid
                break
        elif len(getExercises) == 2:
            if index == 1:
                exercise1 = exercise.exerciseid
                index += 1
                continue
            elif index ==2:
                exercise2 = exercise.exerciseid
                exercise3 = exercise.exerciseid
                break
        elif len(getExercises) == 1:
                exercise1 = exercise.exerciseid
                exercise2 = exercise.exerciseid
                exercise3 = exercise.exerciseid
    
    exercise1 = Exercises.query.filter_by(exerciseid = exercise1).first().exercise
    exercise2 = Exercises.query.filter_by(exerciseid = exercise2).first().exercise
    exercise3 = Exercises.query.filter_by(exerciseid = exercise3).first().exercise



    form = WorkoutForm()
    if form.validate_on_submit():
        set1 = form.set1.data
        set2 = form.set2.data
        set3 = form.set3.data
        index = 1
        for exercise in getExercises:
            if len(getExercises) == 3:
                if index == 1:
                    exercise.reps_completed = set1
                    index +=1
                    continue
                elif index == 2:
                    exercise.reps_completed = set2
                    index += 1
                    continue
                elif index == 3:
                    exercise.reps_completed = set3
                    break
            elif len(getExercises) == 2:
                if index == 1:
                    exercise.reps_completed = set1
                    index += 1
                    continue
                elif index == 2:
                    if set2 > set3:
                        exercise.reps_completed = set2
                        break
                    else:
                        exercise.reps_completed = set3
                        break
            elif len(getExercises) == 1:
                if set1 >set2 and set1 > set3:
                    exercise.reps_completed = set1
                elif set2 > set1 and set2 > set3:
                    exercise.reps_completed = set2
                else:
                    exercise.reps_completed = set3
        db.session.commit()
        return redirect(url_for('log'))


    return render_template('workout.html', title= 'Workout', form=form, exercise1=exercise1, exercise2=exercise2, exercise3=exercise3)

@app.route('/log', methods=['GET','POST'])
@login_required
def log():
    workoutlist = []
    exerciseTable = Exercises.query.all()
    userWorkoutid =Workout.query.filter_by(userid= current_user.userid).order_by(Workout.workoutid.desc()).all()
    newestWorkoutid = Workout.query.filter_by(userid= current_user.userid).order_by(Workout.workoutid.desc()).first()
    if not newestWorkoutid:
        return redirect(url_for('workout'))
    for wid in userWorkoutid:
        workouts = ExercisesInWorkout.query.filter_by(workoutid = wid.workoutid).all()
        workoutlist.append(workouts)
    form = UpdateRepsForm()
    if form.validate_on_submit():
        if form.deleteWorkout:
                newestWorkout= ExercisesInWorkout.query.filter_by(workoutid = newestWorkoutid.workoutid).all()
                for exercise in newestWorkout:
                    db.session.delete(exercise)
        db.session.delete(newestWorkoutid)
        db.session.commit()
        return redirect(url_for('log'))

    return render_template('log.html', title= "Workout Log", exercises= exerciseTable, wid=newestWorkoutid.workoutid, workout1=workoutlist, form=form) 


@app.route('/update/<int:wid>', methods=['GET','POST'])
@login_required
def update(wid):
    getExercises = ExercisesInWorkout.query.filter_by(workoutid = wid).all()
    index =1
    for exercise in getExercises:
        if len(getExercises) == 3:
            if index == 1:
                exercise1 = exercise.exerciseid
                index += 1
                continue
            elif index ==2:
                exercise2 = exercise.exerciseid
                index +=1
                continue
            elif index ==3:
                exercise3 = exercise.exerciseid
                break
        elif len(getExercises) == 2:
            if index == 1:
                exercise1 = exercise.exerciseid
                index += 1
                continue
            elif index ==2:
                exercise2 = exercise.exerciseid
                exercise3 = exercise.exerciseid
                break
        elif len(getExercises) == 1:
                exercise1 = exercise.exerciseid
                exercise2 = exercise.exerciseid
                exercise3 = exercise.exerciseid
    
    exercise1 = Exercises.query.filter_by(exerciseid = exercise1).first().exercise
    exercise2 = Exercises.query.filter_by(exerciseid = exercise2).first().exercise
    exercise3 = Exercises.query.filter_by(exerciseid = exercise3).first().exercise



    form = WorkoutForm()
    if form.validate_on_submit():
        set1 = form.set1.data
        set2 = form.set2.data
        set3 = form.set3.data
        index = 1
        for exercise in getExercises:
            if len(getExercises) == 3:
                if index == 1:
                    exercise.reps_completed = set1
                    index +=1
                    continue
                elif index == 2:
                    exercise.reps_completed = set2
                    index += 1
                    continue
                elif index == 3:
                    exercise.reps_completed = set3
                    break
            elif len(getExercises) == 2:
                if index == 1:
                    exercise.reps_completed = set1
                    index += 1
                    continue
                elif index == 2:
                    if set2 > set3:
                        exercise.reps_completed = set2
                        break
                    else:
                        exercise.reps_completed = set3
                        break
            elif len(getExercises) == 1:
                if set1 >set2 and set1 > set3:
                    exercise.reps_completed = set1
                elif set2 > set1 and set2 > set3:
                    exercise.reps_completed = set2
                else:
                    exercise.reps_completed = set3
        db.session.commit()
        return redirect(url_for('log'))


    return render_template('workout.html', title= 'Workout', form=form, exercise1=exercise1, exercise2=exercise2, exercise3=exercise3)


@app.route('/review/<int:wid>', methods=['GET','POST'])
@login_required
def review(wid):
    form= ReviewForm()
    workoutRated = Reviews.query.filter_by(workoutid = wid).first()
    if workoutRated:
            return "You've already rated this workout, please go back and create a new workout"
    else:
        if form.validate_on_submit():
            print("validated")
            currentRating = Reviews(workoutid=wid, rating= form.rating.data)
            db.session.add(currentRating)
            db.session.commit()
            return redirect(url_for('home'))
        return render_template('review.html', title= 'Review', form=form)
