from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from flask_login import login_required,current_user
from app.decorators import check_confirmed, check_assigned_house, check_manager
from app import models
from app.models import Module, db, User, HouseKeeper, House, add_house_keeper_by_entity, update_by_entity, HOUSEKEEPER, add_by_entity
from app.forms import AssignHouseForm, DeleteHouseForm, AddHouseForm

bp = Blueprint('house', __name__, template_folder='templates/house')


@bp.route('/test')
def test():
    return 'Housepage test.'


@bp.route('/assignhouse', methods=['GET', 'POST'])
#@check_manager
def assignhouse():
    teachers = User.query.filter_by(title=HOUSEKEEPER).order_by(User.email)
    teachers_list = [(i.id, i.email) for i in teachers]
    houses = House.query.order_by(House.year)
    houses_list = [(i.house_id, "House %s in Year %d" % (i.house_name, int(i.year))) for i in houses]
    form = AssignHouseForm()
    form.houses.choices = houses_list
    form.teachers.choices = teachers_list

    if form.validate_on_submit():
        print('submit')
        # study_year = form.study_year.data
        # email = form.teacher_email.data
        # house_name = form.house_name.data
        user = User.query.filter_by(id=form.teachers.data).first()
        house = House.query.filter_by(house_id=form.houses.data).first()
        # house_keeper = HouseKeeper(user.id, module_id=session['moduleId'])
        # add_house_keeper_by_entity(house_keeper)
        house.house_keeper = user.id
        update_by_entity(house)
        user.title = HOUSEKEEPER
        update_by_entity(user)
        flash("assigned house successfully")
        return redirect(url_for('house.assignhouse'))
    return render_template('assign_house.html', form=form)


@bp.route('/deletehouse', methods=['GET', 'POST'])
#@check_manager
def deletehouse():
    # try_house = House(1, 2, 3, "grey")
    # db.session.add(try_house)
    # db.session.commit()
    houses = House.query.order_by(House.year)
    houses_list = [(i.house_id, "House %s in Year %d" % (i.house_name, i.year)) for i in houses]
    form = DeleteHouseForm()
    form.houses.choices = houses_list
    if form.validate_on_submit():
        house = House.query.filter_by(house_id=form.houses.data).first()
        print(house.serialize())
        db.session.delete(house)
        db.session.commit()
        flash("delete successfully")
        return redirect(url_for('house.deletehouse'))
        # print('submit')
        # study_year = form.study_year.data
        # email = form.teacher_email.data
        # house_name = form.house_name.data
        # user = User.query.filter_by(email=email).first()
        # house = House.query.filter_by(year=study_year, house_name=house_name).first()
        # # house_keeper = HouseKeeper(user.id, module_id=session['moduleId'])
        # # add_house_keeper_by_entity(house_keeper)
        # house.house_keeper = user.id
        # update_by_entity(house)
        # user.title = HOUSEKEEPER
        # update_by_entity(user)
        # flash("assigned house successfully")
        # return redirect(url_for('house.assignhouse'))
    return render_template('delete_house.html', form=form)


@bp.route('/addhouse', methods=['GET', 'POST'])
#@check_manager
def addhouse():
    form = AddHouseForm()

    if form.validate_on_submit():
        print('submit')
        study_year = form.study_year.data
        #email = form.teacher_email.data
        house_name = form.house_name.data
        house = House.query.filter_by(year=study_year, house_name=house_name).first()
        if house is not None:
            flash("house already exists")
            return redirect(url_for('house.addhouse'))
        else:
            house = House(None, study_year, 1, house_name)
            add_by_entity(house)
        # house_keeper = HouseKeeper(user.id, module_id=session['moduleId'])
        # add_house_keeper_by_entity(house_keeper)

            flash("add house successfully, you can assign house keeper now.")
            return redirect(url_for('house.assignhouse'))
    return render_template('house/add_house.html', form=form)