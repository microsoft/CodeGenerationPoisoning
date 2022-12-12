import os
from uuid import uuid4

from flask import render_template, flash, send_file, current_app, abort
from flask_login import login_required

from app.reports import bp
from app.models import (
    create_shift_report,
    Category,
    Employees,
    WorkShift,
    csv_to_xlsx,
)
from app.reports.forms import WorkShiftReportsForm


@bp.route('/reports', methods=['GET', 'POST'])
@login_required
def create_reports():
    reports = WorkShiftReportsForm()
    filename = uuid4()

    if reports.validate_on_submit():

        employees = (
            WorkShift.query.filter(
                WorkShift.start_date >= reports.start_date.data,
                WorkShift.end_date <= reports.end_date.data,
                Employees.department == reports.department.data,
            ).outerjoin(Employees).all()
        )

        create_shift_report(employees=employees, filename=filename)
        csv_to_xlsx(filename=filename)

        flash('Отчет сформирован', Category.SUCCESS.title)

    return render_template(
        'reports/reports.html',
        filename=filename,
        reports=reports,
    )


@bp.route('/uploads/<path:filename>', methods=['GET', 'POST'])
@login_required
def download(filename):
    try:
        return send_file(
            os.path.join(
                current_app.config['CSV_UPLOADS_DIRECTORY'],
                f'{filename}.xlsx',
            ),
            attachment_filename=f'{filename}.xlsx',
            mimetype='application/'
                     'vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
        )
    except FileNotFoundError:
        abort(404)
