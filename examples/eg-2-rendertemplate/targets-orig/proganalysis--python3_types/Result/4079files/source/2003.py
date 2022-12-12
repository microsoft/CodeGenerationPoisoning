from ..models import User, Paper, Message, Course, School, Order
from . import per
from flask import render_template, request, session, redirect, url_for, jsonify, abort, flash
from .. import basic


@per.route('/info/<uid>')
@per.route('/')
def info_page(uid=None):
    if uid:
        user = User.query_one(User.u_id == uid)
        courses = None
    else:
        email = session['user']
        user = User.query_one(User.u_email == email)
        courses = eval(user.u_own) if user.u_own else []
    stars = eval(user.u_star) if user.u_star else []
    if user.u_role == 1:
        papers = Paper.query_all(Paper.p_worker == user.u_id)
        return render_template('per/sinfo.html', papers=papers, courses=courses, user=user, stars=stars)
    elif user.u_role == 2:
        _papers = Paper.query_all(Paper.p_creator == user.u_id)
        papers = basic.parse_teacher_papers(_papers)
        return render_template('per/tinfo.html', papers=papers, courses=courses, user=user, stars=stars)
    elif user.u_role == 3:
        school = School.query_one(School.s_id == user.u_school)
        applicants = eval(school.s_applicants) if school.s_applicants else []
        teachers = eval(school.s_teachers) if school.s_teachers else []
        courses = Course.query_all(Course.c_belong == school.s_id)
        return render_template('per/ainfo.html', teachers=teachers, courses=courses, user=user, stars=stars,
                               school=school, applicants=applicants)
    elif user.u_role == 4:
        children = eval(user.u_own)
        return render_template('per/pinfo.html', children=children, stars=stars, user=user)


@per.route('/bind', methods=['POST'])
def bind_gmail():
    data = request.form
    if 'idtoken' in data:
        user_info = basic.verify_google_plus(data['idtoken'])
        if user_info:
            User.update(User.u_email == session['user'], {User.u_gmail: user_info['email']})
        return 'accepted'
    return '', 400


@per.route('/like/<pid>', methods=['DELETE'])
@per.route('/like', methods=['POST', 'GET'])
def like(pid=None):
    if request.method == 'POST':
        p_id = request.values['pid']
        p_title = request.values['title']
        if p_id and p_title:
            _new = dict(p_id=p_id, p_title=p_title)
            User.star(session['user'], _new)
            return 'accepted'
        return 'args error'
    elif request.method == 'GET':
        liked = User.query_one(User.u_email == session['user']).u_star
        posts = eval(liked) if liked else []
        return jsonify(posts)
    elif request.method == 'DELETE' and pid:
        User.unstar(session['user'], pid)
        return 'accepted'


@per.route('/message', methods=['POST', 'GET'])
def message():
    if request.method == 'GET':
        _senders = Message.pull(session['uid'])
        senders = list()
        for _sender in _senders:
            senders.append(_sender.decode())
        return jsonify(senders or [])
    elif request.method == 'POST':
        data = dict()
        data['m_cont'] = request.values['m_cont']
        data['m_to'] = request.values['m_to']
        data['m_from'] = session['uid']
        Message.save(Message(**data))
        return 'accepted'


@per.route('/message/new')
def new_message():
    flag = Message.exist(session['uid'])
    return jsonify({'r': int(flag)})


@per.route('/message/<sender>')
def get_message(sender):
    msgs = Message.query_last(Message.m_to == session['uid'], Message.m_from == sender)
    messages = basic.make_obj_serializable(msgs)
    return jsonify(messages or [])


# 检查用户身份
@per.route('/parent', methods=['POST'])
def bind_parent():
    if request.method == 'POST':
        c_user = User.query_one(User.u_email == session['user'])
        if not c_user or c_user.u_role != 1:
            return abort(403)
        u_email = request.values.get('u_email')
        p_user = User.query_one(User.u_email == u_email)
        if not p_user or p_user.u_role != 4:
            return abort(403)
        User.bind_child(session['user'], u_email)
        return 'accepted'


@per.route('/child')
def show_child():
    if request.method == 'GET':
        user = User.query_one(User.u_email == session['user'])
        if user and user.u_role == 4:
            own = User.query_one(User.u_email == session['user']).u_own
            return jsonify(eval(own) if own else [])
        return jsonify([])


@per.route('/order')
def show_orders():
    p = int(request.args.get('p') or 1)
    p -= 1
    items = Order.query_range(Order.o_buyer == session['uid'], Order.o_finish == 1,
                              order_key=Order.o_id.desc(), start=p*10, stop=p*10+10)
    if items:
        orders = basic.make_obj_serializable(items)
    else:
        orders = []
    return jsonify(orders)


@per.route('/upload/picture', methods=['POST', 'GET'])
def set_avatar():
    if request.method == 'GET':
        return render_template('cos/upload.html', folder='/picture/', sign_name='auth.gen_cos_picsign',
                               file_id=basic.gen_file_id())
    if request.method == 'POST':
        u_pic = eval(request.form.get('result')).get('data').get('access_url')
        User.update(User.u_email == session['user'], {User.u_pic: u_pic})
        return ''


@per.before_request
def required_login():
    if 'info' in request.url:
        return
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    # the best way is keep session immutable
    user = User.query_one(User.u_email == session['user'])
    if not user or user.u_id != session['uid']:
        return redirect(url_for('auth.login'))
