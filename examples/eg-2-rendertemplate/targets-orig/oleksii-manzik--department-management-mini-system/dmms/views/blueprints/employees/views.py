import requests
from flask import Blueprint, render_template, request, redirect, url_for, flash

employees_blueprint = Blueprint('employees', __name__)


@employees_blueprint.route('/employees')
def get_employees():
    """Show all employees"""
    if request.args:
        employees = requests.get('http://localhost:5000/employees',
                                 params=request.args).json()
        dates = {'start': request.args['date_of_birth_start'],
                 'end': request.args['date_of_birth_end']}
    else:
        employees = requests.get('http://localhost:5000/employees').json()
        dates = {}
    data = {}
    # TODO : get department name in '/employees' endpoint response
    departments = requests.get('http://localhost:5000/departments').json()
    for employee in employees:
        value = {
            'name': employee['name'],
            'date_of_birth': employee['date_of_birth'],
            'department': [d['name'] for d in departments
                           if employee['department_id'] == d['id']][0],
            'salary': employee['salary'],
            'link': url_for('employees.get_employee',
                            employee_id=employee['id'])}
        data[employee['id']] = value
    return render_template('employees.html', data=data, dates=dates)


@employees_blueprint.route('/employees/<employee_id>', methods=['GET'])
def get_employee(employee_id):
    """Show specific employee"""
    employee = requests.get('http://localhost:5000/employees',
                            params={'id': [employee_id]}).json()[0]
    # TODO : get department name in '/employees' endpoint response
    departments = requests.get('http://localhost:5000/departments').json()
    data = {'id': employee_id, 'name': employee['name'],
            'date_of_birth': employee['date_of_birth'],
            'department': [d['name'] for d in departments
                           if employee['department_id'] == d['id']][0],
            'salary': employee['salary']}
    return render_template('employee.html', data=data)


@employees_blueprint.route('/employees/edit_employee/<employee_id>',
                           methods=['GET'])
def edit_employee(employee_id):
    """Show edit employee page"""
    employee = requests.get('http://localhost:5000/employees',
                            params={'id': [employee_id]}).json()[0]
    # TODO : get department name in '/employees' endpoint response
    departments = requests.get('http://localhost:5000/departments').json()
    data = {'title': 'Edit employee',
            'message': f"Please edit info for {employee['name']} employee",
            'name': employee['name'],
            'date_of_birth': employee['date_of_birth'],
            'department': [d['name'] for d in departments
                           if employee['department_id'] == d['id']][0],
            'salary': employee['salary']}
    return render_template('employee_raw.html', data=data)


@employees_blueprint.route('/employees/edit_employee/<employee_id>',
                           methods=['POST'])
def save_editing_employee(employee_id):
    """Edit specific employee. All fields must be filled"""
    if request.form.get('cancel'):
        return redirect(url_for('employees.get_employee',
                                employee_id=employee_id))
    name = request.form.get('name')
    date_of_birth = request.form.get('date_of_birth')
    department_name = request.form.get('department')
    salary = request.form.get('salary')
    if not all([name, date_of_birth, department_name, salary]):
        flash("Please fill all fields")
        return redirect(url_for('employees.edit_employee'))
    department = requests.get('http://localhost:5000/departments',
                              params={'name': [department_name]}).json()
    data = f'{{"name": "{name}", "date_of_birth": "{date_of_birth}", ' \
           f'"salary": {salary}, "department_id": "{department["id"]}"}}'
    save = requests.put(f'http://localhost:5000/employees/{employee_id}',
                        data=data,
                        headers={'Content-Type': 'application/json'})
    if save.status_code != 200:
        flash("Sorry your employee wasn't edited. Please try again later")
        return redirect(url_for('employees.edit_employee',
                                employee_id=employee_id))
    return redirect(url_for('employees.get_employees',
                            employee_id=employee_id))


@employees_blueprint.route('/employees/delete_employee/<employee_id>',
                           methods=['GET'])
def delete_employee(employee_id):
    """Delete specific employee"""
    delete = requests.delete(
        f'http://localhost:5000/employees/{employee_id}')
    return redirect(url_for('employees.get_employees'))


@employees_blueprint.route('/employees/add_employee', methods=['GET'])
def add_employee():
    """Show add new employee page"""
    all_departments = requests.get('http://localhost:5000/departments').json()
    data = {'title': 'Create employee',
            'message': 'Please provide info for new employee',
            'departments': [department['name'] for department
                            in all_departments]}
    return render_template('employee_raw.html', data=data)


@employees_blueprint.route('/employees/add_employee', methods=['POST'])
def save_employee():
    """Create new employee. All fields must be filled"""
    if request.form.get('cancel'):
        return redirect(url_for('employees.get_employees'))
    name = request.form.get('name')
    date_of_birth = request.form.get('date_of_birth')
    department_name = request.form.get('department')
    salary = request.form.get('salary')
    # TODO : need to save data that was inputed
    if not all([name, date_of_birth, department_name, salary]):
        flash('Please provide all info of employee')
        return redirect(url_for('employees.add_employee'))
    department = requests.get('http://localhost:5000/departments',
                              params={'name': [department_name]}).json()
    data = f'{{"name": "{name}", "date_of_birth": "{date_of_birth}", ' \
           f'"salary": {salary}, "department_id": "{department["id"]}"}}'
    save = requests.post('http://localhost:5000/employees', data=data,
                         headers={'Content-Type': 'application/json'})
    # TODO : need to save data that was inputed
    if save.status_code != 201:
        flash("Sorry your department wasn't saved. Please try again later")
        return redirect(url_for('employees.add_employee'))
    return redirect(url_for('employees.get_employees'))
