from flask import request, render_template, redirect, url_for, make_response, jsonify
from flask import current_app as app
from .modelos import db, Persona, Tarjeta, Venta

@app.route('/persona/')
def pers():
    personas = Persona.get_all()
    return render_template("persona/index.html",
                           personas=personas,
                           titulo='Personas')


@app.route("/persona/crear", methods=["GET"])
def pers_crear():
    print('request.args')
    print(request.args)
    print('request.base_url')
    print(request.base_url)
    print('request.data')
    print(request.data)
    print('request.form')
    print(request.form)
    print('request.get_json()')
    print(request.get_json())
    print('request.get_data()')
    print(request.get_data())
    print('request.full_path')
    print(request.full_path)
    print('request.headers')
    print(request.headers)
    print('request.method')
    print(request.method)
    print('request.query_string')
    print(request.query_string)
    print('request.referrer')
    print(request.referrer)
    print('request.user_agent')
    print(request.user_agent)
    return render_template("persona/crear.html")

@app.route("/persona/crear", methods=["POST"])
def pers_agregar():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
    if nombre and apellido:
        pers1 = Persona(nombre=nombre, apellido=apellido)
        db.session.add(pers1)
        db.session.commit()
    return redirect(url_for('pers'))


@app.route("/persona/detalle", methods=['GET'])
def pers_detalles():
    persona_id = int(request.args['id'])
    persona = Persona.find_by_id(persona_id)
    tarjeta_id = int(request.args['id'])
    tarjeta = Tarjeta.find_by_id(tarjeta_id)
    return render_template("persona/detalle.html", persona=persona, tarjeta=tarjeta)

@app.route('/persona/delete')
def pers_delete():
    persona_id = int(request.args['id'])
    persona = Persona.find_by_id(persona_id)
    db.session.delete(persona)
    db.session.commit()
    return redirect('/persona')

@app.route('/persona/update', methods=['GET', 'POST'])
def update():
    persona_id = int(request.args['id'])
    persona = Persona.find_by_id(persona_id)
    if request.method == 'POST':
        persona.nombre = request.form.get('nombre')
        persona.apellido = request.form.get('apellido')
        db.session.commit()
        return redirect('/persona')
    else:
        return render_template('/persona/update.html', persona=persona)
