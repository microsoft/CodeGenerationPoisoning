from ..decorators import admin_required
from flask_login import login_required, current_user
from flask import render_template, flash, redirect, url_for
from . import control_room_blueprint
from ..models import User, UserContact, Student, Staff, Parent
from .. import db
from ..auth.forms import StudentForm, ParentForm, StaffForm
from ..picture_handler import add_profile_pic


@control_room_blueprint.route('/edit_profile_for_other_user/<user_name>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_for_other_user(user_name):
    user = User.query.filter_by(user_name=user_name).first()
    if user.student:
        form = StudentForm()
        person = Student.query.filter_by(user_id=current_user.id).first()
        form.student_class.data = person.student_class

    elif user.parent:
        form = ParentForm()
        person = Parent.query.filter_by(user_id=current_user.id).first()
        form.parent_class.data = person.parent_class
        form.student_username.data = person.return_student_user_name()

    else:
        form = StaffForm()
        person = Staff.query.filter_by(user_id=current_user.id).first()

    user_contact = UserContact.query.filter_by(user_id=user.id).first()

    form.first_name.data = person.first_name
    form.middle_name.data = person.middle_name
    form.last_name.data = person.last_name
    form.gender.data = person.gender
    form.religion.data = person.religion
    form.date_of_birth.data = person.date_of_birth
    form.mobile_number.data = user_contact.mobile_number
    form.address.data = user_contact.address
    form.submit.label.text = "Submit Profile [Admin]"

    if form.validate_on_submit():
        if user.student:
            person.student_class = form.student_class.data

        elif user.parent:
            person.parent_class = form.parent_class.data
            student_user = User.query.filter_by(user_name=form.student_username.data).first()
            person.student_id = student_user.id
        else:
            pass

        person.first_name = form.first_name.data
        person.middle_name = form.middle_name.data
        person.last_name = form.last_name.data
        person.gender = form.gender.data
        person.religion = form.religion.data
        person.date_of_birth = form.date_of_birth.data
        user_contact.mobile_number = form.mobile_number.data
        user_contact.address = form.address.data
        if form.picture.data:
            pic = add_profile_pic(form.picture.data, user.user_name)
            user_contact.profile_image = pic

        db.session.commit()

        flash('You have just edited you profile for' + user.user_name)
        return redirect(url_for('main.index'))
    return render_template('account.html', form=form)
