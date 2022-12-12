import csv
import math
import codecs
from datetime import date
from flask import (
    Blueprint, redirect, render_template, url_for,
    session, request, flash)
from flask_login import login_required, current_user
import os
from app import db, models
from app.decorators import check_confirmed
from app.forms import ModuleInfoForm, CommentForm
from app.models import Module, User, Comment, get_avg_stars, add_comment_by_entity, House, Questionnaire, \
    Question_rate, get_question_avg_stars, Student, add_by_entity, update_by_entity, UserModule, get_questionnaire
import sqlite3
import json
from flask import send_from_directory, abort

bp = Blueprint('module_info', __name__, template_folder='templates/module')


@bp.route('/test1', methods=['GET', 'POST'])
def test1():
    module = Module('bbb', 'bbb')
    Module.add_a_module_by_enity(module)
    return 'module test'


@bp.route('/test2', methods=['GET', 'POST'])
def test2():
    return render_template('test2.html')


@bp.route('/test3', methods=['GET', 'POST'])
def test3():
    return render_template('modules_info.html', module=None)


@bp.route('/info', methods=['GET', 'POST'])
@login_required
@check_confirmed
def info():
    title = User.get_user_by_id(current_user.id).title
    module_id = request.args.get("id")
    session['moduleId'] = module_id
    # if session['moduleId'] is None:
    #     module_id = request.args.get("id")
    #     session['moduleId'] = module_id
    # else:
    #     module_id = session['moduleId']
    user_id = current_user.id
    module = Module.query.filter_by(id=module_id).first()
    user = User.query.filter_by(id=user_id).first()
    coordinator = User.query.filter_by(id=module.owner_id).first()
    comment_list = db.session.query(User.id, User.uname, User.img, Comment.module_id, Comment.content, Comment.star,
                                    Comment.date).filter(Comment.owner_id == User.id).filter(
        Comment.module_id == module_id).all()
    avg_star = get_avg_stars(module_id)

    star_dict = {}
    questionnaire = get_questionnaire()
    for q in questionnaire:
        star_dict[q.id] = 0
        avg = get_question_avg_stars(q.id, '3').average
        if avg is None:
            q.avg_star = 0
        else:
            print(avg)
            q.avg_star = round(avg, 1)

    if user.title == models.HOUSEKEEPER:
        return render_template('module_info_teacher.html',
                               module=module,
                               user=user,
                               coordinator=coordinator,
                               commentList=comment_list,
                               totalComments=len(comment_list),
                               avgStar=avg_star,
                               questionnaire=questionnaire,
                               star_dict=json.dumps(star_dict),
                               title=title)
    else:
        # house = House.get_house_by_housekeeper(current_user.id)
        # notification_num = models.get_request_owner_list_count(house.house_id)
        title = current_user.title
        user_module = UserModule.query.filter_by(email=current_user.email, module_id=int(module_id)).first()
        not_add = False
        can_comment = False
        if user_module is None:
            not_add = True
        elif user_module.status == 0:
            not_add = False
        elif user_module.status == 1:
            not_add = False
            can_comment = True



        return render_template('module_info_student.html',
                               module=module,
                               user=user,
                               coordinator=coordinator,
                               commentList=comment_list,
                               totalComments=len(comment_list),
                               avgStar=avg_star,
                               not_add=not_add,
                               can_comment=can_comment,
                               # notification_num=notification_num,
                               title=title,
                               questionnaire=questionnaire,
                               star_dict=json.dumps(star_dict))


@bp.route('/edit', methods=['GET', 'POST'])
@login_required
@check_confirmed
def edit():
    title = User.get_user_by_id(current_user.id).title
    module = Module.query.filter_by(id=session.get('moduleId')).first()
    return render_template('edit_info.html', module=module,
                           title=title)


@bp.route('/save', methods=['GET', 'POST'])
@login_required
@check_confirmed
def save():
    form = ModuleInfoForm()
    module_id = session.get('moduleId')
    module_name = form.name.data
    module_desc = form.description.data
    module = Module(module_name, module_desc, current_user.id, None)
    module.id = module_id
    # if form.validate_on_submit():
    if Module.update_a_module_by_enity(module):
        return redirect(url_for('module_info.info', id=module_id))
    else:
        return 'Save module info error ..........'


@bp.route('/comment', methods=['GET', 'POST'])
@login_required
@check_confirmed
def comment():
    today = date.today()
    owner_id = current_user.id
    module_id = session.get('moduleId')
    form = CommentForm()
    star_dict = json.loads(form.star.data)
    avg_star = 0

    for k in star_dict:
        avg_star += star_dict[k]

    avg_star = math.ceil(avg_star / len(star_dict))

    content = form.comment.data
    comment = Comment(owner_id, module_id, content, avg_star, 0, today)
    add_comment_by_entity(comment)

    question_rate_list = []
    for k in star_dict:
        q = Question_rate(k, module_id, star_dict[k], comment.id)
        question_rate_list.append(q)

    Question_rate.add_question_rate_list(question_rate_list)
    return redirect(url_for('module_info.info', id=module_id))


@bp.route('/download', methods=['GET', 'POST'])
@login_required
@check_confirmed
def download():
    student = Student.get_full_info_by_id(current_user.id)
    houseid = student.house_id
    try:
        conn = db.engine.raw_connection()
        path_ = get_temp_folder() + 'student.csv'
        with open(path_, 'w+', newline='') as write_file:
            cursor = conn.cursor()
            cursor.execute('SELECT uname,email FROM user, student WHERE student.user_id ='
                           ' user.id AND student.house_id = ' + str(houseid))
            csv_writer = csv.writer(write_file)
            csv_writer.writerow([i[0] for i in cursor.description])
            csv_writer.writerows(cursor)

        try:
            return send_from_directory(get_temp_folder(), filename='student.csv', as_attachment=True)
        except FileNotFoundError:
            abort(404)

    except sqlite3.Error as e:
        print(e)
    finally:
        conn.close()
    abort(404)


@bp.route('/upload', methods=['GET', 'POST'])
@login_required
@check_confirmed
def upload():
    if request.method == "POST":
        if request.files:
            csvFile = request.files["csv"]

            if csvFile.filename == '':
                return redirect(url_for('namelist.nameli'))
            temp_file = os.path.join(get_temp_folder(), csvFile.filename)
            csvFile.save(temp_file)
            process_csv(temp_file)
            os.remove(temp_file)
            flash("assigned house successfully")
            return redirect(url_for('namelist.nameli', upload_status=True))
    return "Upload failed."


def get_temp_folder():
    path = os.getcwd() + '//app//static//temp//' + str(current_user.id) + '//'
    folder = os.path.exists(path)

    if not folder:
        os.makedirs(path)

    return path


def process_csv(path):
    house = House.get_house_by_housekeeper(current_user.id)
    csv_file = codecs.open(path, 'r', 'utf-8-sig')
    dict_reader = csv.DictReader(csv_file)
    result = []

    for item in dict_reader:
        student = Student.query.filter_by(student_email=item["email"]).first()
        if student is None:
            student = Student(house_id=house.house_id, module_id=None, student_email=item["email"])
            add_by_entity(student)
        else:
            student.house_id = house.house_id
            update_by_entity(student)
        result.append(item["email"])
    flash("upload successfully")
    print(result)
    return True


@bp.route('/upload_module', methods=['GET', 'POST'])
@login_required
@check_confirmed
def upload_module():
    if request.method == "POST":
        if request.files:
            csvFile = request.files["csv"]
            if csvFile.filename == '':
                return redirect(url_for('module_info.info'))
            temp_file = os.path.join(get_temp_folder(), csvFile.filename)
            csvFile.save(temp_file)
            process_csv_module(temp_file)
            os.remove(temp_file)
            return redirect(url_for('module_info.info',id=int(session['moduleId']), upload_status=True))

    return "Upload failed."


def process_csv_module(path):
    module_id = int(session['moduleId'])
    csvFile = codecs.open(path, 'r', 'utf-8-sig')
    dict_reader = csv.DictReader(csvFile)
    # print (dict_reader)
    result = []
    for item in dict_reader:
        user_module = UserModule.query.filter_by(email=item["email"], module_id=module_id).first()
        if user_module is None:
            user_module = UserModule(email=item["email"], module_id=module_id, status=1)
            add_by_entity(user_module)
        else:
            user_module.status = 1
            update_by_entity(user_module)
        result.append(item["email"])
    print(result)
    return 'Upload Success'

