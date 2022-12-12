import requests
from flask import Blueprint, render_template, request, redirect, url_for, flash

departments_blueprint = Blueprint('departments', __name__)


@departments_blueprint.route('/departments', methods=['GET'])
def get_departments():
    """Show all departments"""
    all_departments = requests.get('http://localhost:5000/departments').json()
    data = {}
    for department in all_departments:
        sum_salary = sum([employee['salary'] for employee
                          in department['employees']])
        num_employees = len(department['employees'])
        avg_salary = sum_salary / num_employees if num_employees else '-'
        link = url_for('departments.get_department',
                       department_id=department['id'])
        value = {'avg_salary': avg_salary, 'link': link}
        data[department['name']] = value
    return render_template('departments.html', data=data)


@departments_blueprint.route('/departments/<department_id>', methods=['GET'])
def get_department(department_id):
    """Show specific department"""
    department = requests.get('http://localhost:5000/departments',
                              params={'id': [department_id]}).json()[0]
    data = {'id': department_id, 'name': department['name'], 'employees': {}}

    if request.args:
        start = request.args['date_of_birth_start']
        end = request.args['date_of_birth_end']
        # TODO : add filter by birthday to API
        department['employees'] = [e for e in department['employees']
                                   if start <= e['date_of_birth'] <= end]
        dates = {'start': start,
                 'end': end}
    else:
        dates = {}
    for employee in department['employees']:
        value = {
            'name': employee['name'],
            'date_of_birth': employee['date_of_birth'],
            'salary': employee['salary'],
            'link': url_for('employees.get_employee',
                            employee_id=employee['id'])}
        data['employees'][employee['id']] = value
    return render_template('department.html', data=data, dates=dates)


@departments_blueprint.route('/departments/edit_department/<department_id>',
                             methods=['GET'])
def edit_department(department_id):
    """Show edit department page"""
    department = requests.get('http://localhost:5000/departments',
                              params={'id': [department_id]}).json()[0]
    data = {'title': 'Edit department',
            'message': f"Please edit info for {department['name']} department",
            'name': department['name']}
    return render_template('department_raw.html', data=data)


@departments_blueprint.route('/departments/edit_department/<department_id>',
                             methods=['POST'])
def save_editing_department(department_id):
    """Edit department page. Name of department must be filled"""
    if request.form.get('cancel'):
        return redirect(url_for('departments.get_department',
                                department_id=department_id))
    name = request.form.get('name')
    if not name:
        flash("Name of department can't be empty")
        return redirect(url_for('departments.edit_department'))
    data = f'{{"name": "{name}"}}'
    save = requests.put(f'http://localhost:5000/departments/{department_id}',
                        data=data,
                        headers={'Content-Type': 'application/json'})
    if save.status_code != 200:
        flash("Sorry your department wasn't edited. Please try again later")
        return redirect(url_for('departments.edit_department'))
    return redirect(url_for('departments.get_department',
                            department_id=department_id))


@departments_blueprint.route('/departments/delete_department/<department_id>',
                             methods=['GET'])
def delete_department(department_id):
    """Delete specific department"""
    delete = requests.delete(
        f'http://localhost:5000/departments/{department_id}')
    # department can't be deleted if some employee is assigned to it.
    # if it is so API would return message why employee can't be deleted
    if delete.status_code != 200:
        flash(delete.text)
        return redirect(url_for('departments.get_department',
                                department_id=department_id))
    return redirect(url_for('departments.get_departments'))


@departments_blueprint.route('/departments/add_department', methods=['GET'])
def add_department():
    """Show add department page"""
    data = {'title': 'Create department',
            'message': 'Please provide info for new department'}
    return render_template('department_raw.html', data=data)


@departments_blueprint.route('/departments/add_department', methods=['POST'])
def save_department():
    """Create new department. Name of department must be filled"""
    if request.form.get('cancel'):
        return redirect(url_for('departments.get_departments'))
    name = request.form.get('name')
    if not name:
        flash('Please provide name of department')
        return redirect(url_for('departments.add_department'))
    data = f'{{"name": "{name}"}}'
    save = requests.post('http://localhost:5000/departments', data=data,
                         headers={'Content-Type': 'application/json'})
    if save.status_code != 201:
        flash("Sorry your department wasn't saved. Please try again later")
        return redirect(url_for('departments.add_department'))
    return redirect(url_for('departments.get_departments'))
