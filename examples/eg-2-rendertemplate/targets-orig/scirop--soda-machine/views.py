from flask import render_template, request
import models
from app import app

# Declaring views
@app.route('/')
def index():
    machines = models.Machine.query.all()
    return render_template('index.html', machines=machines)

@app.route('/addmachine', methods=['GET', 'POST'])
def addmachine():
    # render the basic template when GET method is called
    if request.method == 'GET':
        return render_template('addmachine.html')

    # this works for POST calls
    machine_name = request.form.get('name_field')
    machine_capacity = request.form.get('capacity_field')
    sodas = request.form.get('sodas_field')

    creation_response = models.create_machine(machine_name, machine_capacity, sodas)
    # Check for error calls vs success calls
    if isinstance(creation_response, str):
        error = creation_response
        machine = None
    else:
        error = None
        machine = creation_response
    return render_template('addmachine.html', machine=machine, error = error)

@app.route('/removemachine', methods=['GET', 'POST'])
def removemachine():
    if request.method == 'GET':
        machines = models.Machine.query.all()
        return render_template('removemachine.html', machines=machines)
    machine_name = (request.form.get('name_field'))
    deletion_reponse = models.delete_machine(machine_name)
    machines = models.Machine.query.all()
    if deletion_reponse:
        machine = machine_name
        error = None
    else:
        machine = None
        error = "No Machine found with that name"
    return render_template('removemachine.html', machines=machines, machine=machine, error = error)


@app.route('/addsodas', methods=['GET', 'POST'])
def addsodas():
    machines = models.Machine.query.all()
    if request.method == 'GET':
        return render_template('addsodas.html', machines = machines)

    machine_name = request.form.get('name_field')
    new_sodas = request.form.get('sodas_field')
    creation_response = models.add_sodas(machine_name, new_sodas)
    if creation_response=="success":
        error = None
        success = "Sodas added to machine successfully."
    else:
        error = creation_response
        success = None
    return render_template('addsodas.html', machines = machines, success=success, error = error)

@app.route('/removesodas', methods=['GET', 'POST'])
def removesodas():
    if request.method == 'GET':
        machines = models.Machine.query.all()
        return render_template('removesodas.html', machines=machines)
    machine_name = (request.form.get('name_field'))
    pop_sodas = request.form.get('sodas_field')
    deletion_reponse = models.delete_sodas(machine_name, pop_sodas)
    machines = models.Machine.query.all()
    if deletion_reponse=="success":
        success = "Sodas removed from machine successfully."
        error = None
    else:
        success = None
        error = deletion_reponse
    return render_template('removesodas.html', machines=machines, success=success, error = error)
