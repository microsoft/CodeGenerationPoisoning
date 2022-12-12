from flask import render_template, redirect, request, url_for, flash, session
from ..decorators import permission_required
from flask import render_template
from flask_login import login_required, current_user
from . import courses_blueprint
from ..models import User, Permission, Course, Staff
from .forms import AddCourseForm, EditCourseForm
from .. import db


@courses_blueprint.route('/view_courses', methods=['GET'])
@login_required
@permission_required(Permission.VIEW_COURSES)
def view_courses():
    courses = Course.query.all()
    return render_template('courses.html', courses=courses)


@courses_blueprint.route('/edit_courses/<int:edit_course_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.EDIT_COURSES)
def edit_courses(edit_course_id):
    course = Course.query.get(edit_course_id)

    if edit_course_id == 0:
        form = AddCourseForm()
    else:
        form = EditCourseForm()
        form.course_name.data = course.name
        form.course_abr.data = course.abbreviation
        form.course_max_score.data = course.max_score
        form.course_success_score.data = course.success_score
        form.course_teacher.data = course.course_teacher

    if form.validate_on_submit():
        if edit_course_id == 0:
            course = Course(name=form.course_name.data, abbreviation=form.course_abr.data,
                            max_score=form.course_max_score.data,
                            success_score=form.course_success_score.data, course_teacher=form.course_teacher.data,
                            added_by=current_user.user_name, edited_by=current_user.user_name)
            db.session.add(course)
        else:
            course.name = form.course_name.data
            course.abbreviation = form.course_abr.data
            course.max_score = form.course_max_score.data
            course.success_score = form.course_success_score.data
            course.course_teacher = form.course_teacher.data
            course.edited_by = current_user.user_name

        db.session.commit()
        return redirect(url_for('courses.edit_courses', edit_course_id=0))

    courses = Course.query.all()
    return render_template('edit_courses.html', courses=courses, form=form)
