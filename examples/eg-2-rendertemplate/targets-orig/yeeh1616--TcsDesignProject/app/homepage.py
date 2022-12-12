from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from flask_login import login_required,current_user
from app.decorators import check_confirmed, check_assigned_house
from app import models
from app.forms import ModuleInfoForm
from app.models import Module, db, House, get_all_user, add_house_keeper_by_entity, Request, User, UserModule, \
    add_by_entity, HOUSEKEEPER, MANAGER
from flask_paginate import Pagination, get_page_parameter

bp = Blueprint('main', __name__,template_folder = 'templates')


@bp.route('/test')
def test():
    # house = House(module=1, house_name="house3")
    # db.session.add(house)
    # db.session.commit()
    #db.create_all()
    house = House(None, 2019, None, 'house1')
    add_house_keeper_by_entity(house)
    return get_all_user()


@bp.route('/test2')
def test2():
    house = House.query.first()
    print(house.serialize())
    return "Hello, test!"


@bp.route('/')
@bp.route('/home')
@login_required
@check_confirmed
@check_assigned_house
def home():
    moduleList = Module.query.filter_by(owner_id=current_user.id).all()
    notification_num = 0
    if current_user.title == HOUSEKEEPER:
        moduleList = Module.query.filter_by(owner_id=current_user.id).all()
        house = House.get_house_by_housekeeper(current_user.id)
        if house is None:
            notification_num = 0
        else:
            notification_num = models.get_request_owner_list_count(house.house_id)
    else:
        moduleList = db.session.query(Module.id, Module.name, Module.description, Module.owner_id, Module.img).filter(
            Module.id == UserModule.module_id).filter(UserModule.email == current_user.email).all()
    title = current_user.title
    if title == MANAGER:
        return redirect(url_for('house.addhouse'))
    else:
        return render_template('index.html', moduleList=moduleList, notification_num=notification_num, title=title)


@bp.route('/add_module_page', methods=['GET', 'POST'])
@login_required
@check_confirmed
def add_module_page():
    return render_template('module/add_module.html')


@bp.route('/add_module', methods=['GET', 'POST'])
@login_required
@check_confirmed
def add_module():
    form = ModuleInfoForm()
    module_name = form.name.data
    module_desc = form.description.data
    module = Module(module_name, module_desc, current_user.id, None)
    if Module.add_a_module_by_enity(module) is not None:
        return redirect(url_for('main.home'))
    else:
        return 'Add module info error ..........'


@bp.route('/all_module', methods=['GET', 'POST'])
@login_required
@check_confirmed
def all_module():

    search_term = request.args.get("search")
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 10
    offset = (page - 1) * per_page
    if search_term is None or 0:
        all_modules = db.session.query(Module.id, Module.name, User.uname).filter(
            Module.owner_id == User.id).all()
        # all_modules = Module.query.all()
    else:
        all_modules = db.session.query(Module.id, Module.name, User.uname).filter(
            Module.owner_id == User.id).filter(Module.name.like("%" + search_term + "%")).all()
        # all_modules = Module.query.filter_by(name=search_term)
    all_modules_c = []
    had_modules = UserModule.query.filter_by(email=current_user.email)
    for module in all_modules:
        if not had_module(had_modules, module):
            all_modules_c.append(module)
    pagination = Pagination(page=page,
                            total=len(all_modules_c),
                            search=True,
                            record_name='all_modules_c',
                            per_page=per_page,
                            show_single_page=False,
                            link='<li><a class="pgn__num" href="{0}">{1}</a></li>')

    pagination.current_page_fmt = '<li><span class="pgn__num current">{0}</span></li>'
    pagination.prev_page_fmt = '<li><a class="pgn__prev" href="{0}">{1}</a></li>'
    pagination.next_page_fmt = '<li><a class="pgn__next" href="{0}">{1}</a></li>'
    pagination.gap_marker_fmt = '<li><span class="pgn__num dots">…</span></li>'
    pagination.link = '<li><a class="pgn__num" href="{0}">{1}</a></li>'
    pagination.link_css_fmt = '<div class="{0}{1}"><ul>'
    pagination.prev_disabled_page_fmt = ''
    pagination.next_disabled_page_fmt = ''

    return render_template('module/all_modules.html',
                           all_modules=all_modules_c,
                           pagination=pagination,
                           search=search_term)


@bp.route('/add_module_student', methods=['GET', 'POST'])
@login_required
@check_confirmed
def add_module_student():
    module_id = int(request.args.get("moduleId"))
    userModule = UserModule(current_user.email, module_id, 0)
    add_by_entity(userModule)
    return redirect(url_for("main.all_module"))

@bp.route('/hello')


def hello():
    # models.create_all_table()
    # models.add_a_user("yeye2","bbb","bbb","bbb", False, None)
    print(models.get_user_by_name("yeye2"))
    return "Hello, World!"

def had_module(had_modules, module):
    for had_module in had_modules:
        if had_module.module_id == module.id:
            return True
    return False
