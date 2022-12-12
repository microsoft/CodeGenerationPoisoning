from datetime import date
from datetime import datetime
from flask_paginate import Pagination, get_page_parameter

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from flask_login import login_required, current_user

from app import models
from app.decorators import check_confirmed, check_assigned_house
from app.forms import ModuleInfoForm, RequestForm
from app.models import Module, House, User, Student, Request

bp = Blueprint('namelist', __name__, template_folder='templates/module')


@bp.route('/test')
def test():
    return 'Namelist test.'


@bp.route('/namelist', methods=['GET', 'POST'])
@login_required
@check_confirmed
def nameli():
    user_temp = User.get_user_by_id(current_user.id)
    search = False
    q = request.args.get('q')
    if q:
        search = True
    if user_temp.title == models.HOUSEKEEPER:
        return namelist_teacher(search)
    elif user_temp.title == models.STUDENT:
        return namelist_student(search)


def namelist_teacher(search):
    house = House.get_house_by_housekeeper(current_user.id)
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 10
    offset = (page - 1) * per_page
    namelist = models.get_namelist_by_hid(house.house_id, per_page, offset)

    pagination = Pagination(page=page,
                            total=models.get_namelist_count(house.house_id),
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

    return render_template('module/namelist.html',
                           request_owner_list=namelist,
                           pagination=pagination)


def namelist_student(search):
    student = Student.get_full_info_by_id(current_user.id)
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 10
    offset = (page - 1) * per_page
    namelist = models.get_namelist_by_hid(student.house_id, per_page, offset)

    pagination = Pagination(page=page,
                            total=models.get_namelist_count(student.house_id),
                            search=search,
                            record_name='namelist',
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

    return render_template('module/namelist_student.html',
                           request_owner_list=namelist,
                           pagination=pagination)




