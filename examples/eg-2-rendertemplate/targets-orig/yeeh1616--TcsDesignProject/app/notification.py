from datetime import date
from datetime import datetime
from datetime import timedelta
from flask_paginate import Pagination, get_page_parameter

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from flask_login import login_required, current_user

from app import models
from app.decorators import check_confirmed, check_assigned_house
from app.forms import ModuleInfoForm, RequestForm
from app.models import Module, House, User, Student, Request

bp = Blueprint('notification', __name__, template_folder='templates')


@bp.route('/test')
def test():
    return 'Notification test.'


@bp.route('/request_page', methods=['GET', 'POST'])
@login_required
@check_confirmed
def request_page():
    user_temp = User.get_user_by_id(current_user.id)
    if user_temp.title == models.HOUSEKEEPER:
        search = False
        q = request.args.get('q')
        if q:
            search = True
        return request_page_teacher(search)
    elif user_temp.title == models.STUDENT:
        return request_page_student()


def request_page_student():
    # module_id = session.get('moduleId')
    student = Student.get_full_info_by_email(current_user.email)
    if student is None:
        flash("You do not have a house yet")
        redirect(url_for('main.home'))
    switching_request = Request.get_request_by_owner_id(current_user.id)

    if switching_request is not None:
        my_house = House.get_house_by_id(switching_request.house_from)
        target_house = House.get_house_by_id(switching_request.house_to)
        switching_request.status_txt = models.status_dict.get(switching_request.status)

        d1 = datetime.strptime(switching_request.send_date, '%Y-%m-%d')
        d2 = datetime.now()
        delta = d2 - d1
        switching_request.unfrozen_date = (d1 + timedelta(days=7)).strftime("%Y-%m-%d")
        if delta.days <= 7:
            switching_request.is_frozen = True
        else:
            switching_request.is_frozen = False

        return render_template('notification/request_result_page_student.html',
                               my_house=my_house,
                               target_house=target_house,
                               request=switching_request)
    current_house = House.query.filter_by(house_id=student.house_id).first()
    house_list = House.query.filter_by(year=current_house.year)

    return render_template('notification/request_student.html',
                           house_list=house_list,
                           student=student)


def request_page_teacher(search):
    f = request.args.get("filter")
    house = House.get_house_by_housekeeper(current_user.id)
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 10
    offset = (page - 1) * per_page

    if f is None or 0:
        request_owner_list = models.get_request_owner_list_by_hid_filter(house.house_id, 0, per_page, offset)
        total = models.get_request_owner_list_count_by_status(house.house_id, 0)
    else:
        request_owner_list = models.get_request_owner_list_by_hid_filter(house.house_id, f, per_page, offset)
        total = models.get_request_owner_list_count_by_status(house.house_id, f)

    pagination = Pagination(page=page,
                            total=total,
                            search=search,
                            record_name='request_owner_list',
                            per_page=per_page,
                            show_single_page=True,
                            link='<li><a class="pgn__num" href="{0}">{1}</a></li>')

    pagination.current_page_fmt = '<li><span class="pgn__num current">{0}</span></li>'
    pagination.prev_page_fmt = '<li><a class="pgn__prev" href="{0}">{1}</a></li>'
    pagination.next_page_fmt = '<li><a class="pgn__next" href="{0}">{1}</a></li>'
    pagination.gap_marker_fmt = '<li><span class="pgn__num dots">…</span></li>'
    pagination.link = '<li><a class="pgn__num" href="{0}">{1}</a></li>'
    pagination.link_css_fmt = '<div class="{0}{1}"><ul>'
    pagination.prev_disabled_page_fmt = ''
    pagination.next_disabled_page_fmt = ''

    return render_template('notification/request_teacher.html',
                           request_owner_list=request_owner_list,
                           pagination=pagination,
                           filter=f)


@bp.route('/accept_request', methods=['GET', 'POST'])
@login_required
@check_confirmed
def accept_request():
    request_id = request.args.get("request_id")
    Request.accept_request_by_id(request_id)
    return redirect(url_for('notification.request_page'))


@bp.route('/reject_request', methods=['GET', 'POST'])
@login_required
@check_confirmed
def reject_request():
    request_id = request.args.get("request_id")
    Request.reject_request_by_id(request_id)
    return redirect(url_for('notification.request_page'))


@bp.route('/confirm_request', methods=['GET', 'POST'])
@login_required
@check_confirmed
def confirm_request():
    request_id = request.args.get("request_id")
    Request.confirm_request_by_id(request_id)
    return redirect(url_for('notification.request_page'))


@bp.route('/send_request', methods=['GET', 'POST'])
@login_required
@check_confirmed
def send_request():
    form = RequestForm()
    my_house = House.get_house_by_id(form.houseFrom.data)
    target_house = House.get_house_by_id(form.houseTo.data)

    request = Request.get_request_by_owner_id(current_user.id)
    if request is None:
        request = Request(current_user.id, my_house.house_id, target_house.house_id, form.reason.data, models.PENDING, date.today(), None, 0)
        Request.add_request_by_entity(request)
        request.status_txt = models.status_dict.get(request.status)

        if request.send_date == date.today().strftime("%Y-%m-%d"):
            request.is_frozen = True
        else:
            request.is_frozen = False

        return render_template('notification/request_result_page_student.html',
                                my_house=my_house,
                                target_house=target_house,
                                request=request)
    else:
        return redirect(url_for('notification.request_page'))
