from flask import request, render_template, flash, redirect, url_for, session, abort, jsonify
from ..models import User, School, Order, Course
from .. import basic
from . import sch


@sch.route('/apply', methods=['POST', 'GET'])
def apply():
    if request.method == 'GET':
        return render_template('sch/apply.html')
    if request.method == 'POST':
        name = request.values.get('school-name')
        user = User.query_one(User.u_email == session['user'])
        if user.u_role == 2:
            if School.query_one(School.s_name == name) is None:
                flash('No school named %s' % name)
            else:
                School.add_applicant(session['uid'], name)
                flash('Your application has been submitted')
            return redirect(url_for('sch.apply'))
        elif user.u_role == 3:
            if School.query_one(School.s_name == name):
                flash('This school already existed')
            else:
                School.insert(School(s_name=name, s_pic=basic.SCHOOL_PIC))
                School.commit()
                s_id = School.query_one(School.s_name == name).s_id
                User.update(User.u_email == user.u_email, {User.u_school: s_id})
                flash('Your school has been built up')
            return redirect(url_for('sch.apply'))


@sch.route('/accept', methods=['POST'])
def accept():
    admin = User.query_one(User.u_email == session['user'])
    if admin and admin.u_role == 3:
        users = request.form.getlist('accepted')
        for user in users:
            School.add_teacher(user, admin.u_school)
        return 'Operation succeed'
    return abort(403)


@sch.route('/orders/<c_id>')
def show_orders(c_id):
    if Course.query_one(Course.c_id == c_id).c_belong == User.query_one(User.u_email == session['user']).u_school:
        p = int(request.args.get('p') or 1)
        p -= 1
        items = Order.query_range(Order.o_course == c_id, start=p*10, stop=p*10+10)
        if items:
            orders = basic.make_obj_serializable(items)
        else:
            orders = []
        return jsonify(orders)
    return ''


@sch.route('/upload/picture', methods=['POST', 'GET'])
def set_avatar():
    if request.method == 'GET':
        return render_template('cos/upload.html', folder='/picture/', sign_name='auth.gen_cos_picsign',
                               file_id=basic.gen_file_id())
    if request.method == 'POST':
        s_pic = eval(request.form.get('result')).get('data').get('access_url')
        admin = User.query_one(User.u_email == session['user'])
        School.update(School.s_id == admin.u_school, {School.s_pic == s_pic})
        return ''


@sch.before_request
def required_login():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    user = User.query_one(User.u_email == session['user'])
    if not user or user.u_id != session['uid']:
        return redirect(url_for('auth.login'))
