from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

flask_app = Flask(__name__)

# flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://Memo:77579481@localhost/tarea2'
flask_app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'postgres://zyteiqnwthgodv:d0bba4bef2ee989e71281e6712ea2c710f7b2cdccce8a9c99e9a7c5562f7a36e@ec2-52-87-135-240.compute-1.amazonaws.com:5432/d84fihe3ickqc4'
flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(flask_app)

# ruta = 'http://localhost:5000/'
ruta = 'https://tarea2-iic3103-quememo.herokuapp.com/'

Hamburguesa_Ingrediente = db.Table('Hamburguesa_Ingrediente',
                                   db.Column('hamburguesa_id', db.Integer, db.ForeignKey('hamburguesa.id'), primary_key=True),
                                   db.Column('ingrediente_id', db.Integer, db.ForeignKey('ingrediente.id'), primary_key=True)
                                   )


class Hamburguesa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ingredientes = db.relationship('Ingrediente', secondary=Hamburguesa_Ingrediente, lazy='subquery', backref=db.backref('hamburguesas', lazy=True))
    nombre = db.Column(db.String(), nullable=False)
    precio = db.Column(db.Integer, nullable=False)
    descripcion = db.Column(db.String(), nullable=False)
    imagen = db.Column(db.String(), nullable=False)

    def to_json(self):
        rutas_ingredientes = [{"path": f"{ruta}ingrediente/{ingrediente.id}"} for ingrediente in self.ingredientes]
        return {"id": self.id, "nombre": self.nombre, "precio": self.precio, "descripcion": self.descripcion, "imagen": self.imagen,
                "ingredientes": rutas_ingredientes}


class Ingrediente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String, nullable=False)
    descripcion = db.Column(db.String, nullable=False)

    def to_json(self):
        return {"id": self.id,
                "nombre": self.nombre,
                "descripcion": self.descripcion}


@flask_app.route("/")
def index():
    return render_template('index.html')


@flask_app.route("/hamburguesa")
def get_hamburguesas():
    total_hamburguesas = Hamburguesa.query.all()
    return jsonify([hamburguesa.to_json() for hamburguesa in total_hamburguesas]), "200 resultados obtenidos"


@flask_app.route("/hamburguesa", methods=['POST'])
def create_hamburguesa():
    recibido = request.json
    permitidos = ["nombre", "precio", "descripcion", "imagen"]
    for parametro in permitidos:
        if parametro not in recibido:
            return jsonify('Algún parametro falta'), '400 input invalido'
    if not isinstance(recibido["precio"], int):
        return jsonify('El precio no es un número'), '400 input invalido'

    for parametro in permitidos:
        if parametro == "precio":
            continue
        if len(recibido[parametro]) == 0:
            return jsonify("Algun parametro está vacío"), '400 input invalido'

    nueva_h = Hamburguesa(nombre=recibido['nombre'], precio=recibido['precio'], descripcion=recibido['descripcion'], imagen=recibido['imagen'])
    db.session.add(nueva_h)
    db.session.commit()
    return nueva_h.to_json(), "201 hamburguesa creada"


@flask_app.route("/hamburguesa/<id_h>")
def get_hamburguesa_con_id(id_h):
    try:
        id_h = int(id_h)
    except ValueError:
        return jsonify('ID invalido'), '400 id invalido'

    buscada = Hamburguesa.query.get(id_h)
    if buscada is None:
        return jsonify('La hamburguesa no existe'), '404 hamburguesa inexistente'
    else:
        return buscada.to_json(), '200 operacion exitosa'


@flask_app.route("/hamburguesa/<id_h>", methods=['DELETE'])
def delete_hamburguesa(id_h):
    try:
        id_h = int(id_h)
    except ValueError:
        return jsonify('ID invalido'), '400 id invalido'
    buscada = Hamburguesa.query.get(id_h)
    if buscada is None:
        return jsonify('No existe esa hamburguesa'), '404 hamburguesa inexistente'
    else:
        db.session.delete(buscada)
        db.session.commit()
        return jsonify('Hamburguesa borrada'), '200 hamburguesa eliminada'


@flask_app.route("/hamburguesa/<id_h>", methods=['PATCH'])
def update_hamburguesa(id_h):
    recibido = request.json
    try:
        id_h = int(id_h)
    except ValueError:
        return jsonify('ID invalido'), '400 id invalido'
    permitidos = ["nombre", "precio", "descripcion", "imagen"]
    for parametro in recibido:
        if parametro not in permitidos:
            return jsonify('Hay un parametro invalido'), '400 parametros invalidos'

    for parametro in recibido:
        if parametro == "precio":
            continue
        if len(recibido[parametro]) == 0:
            return jsonify("Algun parametro está vacío"), '400 input invalido'

    if "precio" in recibido:
        try:
            recibido["precio"] = int(recibido["precio"])
        except ValueError:
            return jsonify("Precio no es numero"), "400 parametro invalido"

    hamburguesa_buscada = Hamburguesa.query.get(id_h)
    if hamburguesa_buscada is None:
        return jsonify("No existe esa hamburguesa"), '404 hamburguesa inexistente'

    if "nombre" in recibido:
        hamburguesa_buscada.nombre = recibido["nombre"]
    if "precio" in recibido:
        hamburguesa_buscada.precio = recibido["precio"]
    if "descripcion" in recibido:
        hamburguesa_buscada.descripcion = recibido["descripcion"]
    if "imagen" in recibido:
        hamburguesa_buscada.imagen = recibido["imagen"]
    db.session.commit()
    return hamburguesa_buscada.to_json(), "200 operacion exitosa"


@flask_app.route("/hamburguesa/<id_h>/ingrediente/<id_i>", methods=['DELETE'])
def delete_ingrediente_de_una_hamburguesa(id_h, id_i):
    try:
        id_h = int(id_h)
        id_i = int(id_i)
    except ValueError:
        return jsonify('ID invalido'), '400 id invalido'

    hamburguesa_buscada = Hamburguesa.query.get(id_h)
    ingrediente_buscado = Ingrediente.query.get(id_i)

    if hamburguesa_buscada is None:
        return jsonify('No existe esa hamburguesa'), '404 hamburguesa inexistente'
    if ingrediente_buscado is None:
        return jsonify('No existe ese ingrediente'), '404 ingrediente inexistente'
    if ingrediente_buscado not in hamburguesa_buscada.ingredientes:
        return jsonify('El ingrediente no está en esa hamburguesa'), '404 Ingrediente inexistente en la hamburguesa'

    hamburguesa_buscada.ingredientes.remove(ingrediente_buscado)
    db.session.commit()
    return jsonify('Ingrediente eliminado'), '200 ingrediente retirado'


@flask_app.route("/hamburguesa/<id_h>/ingrediente/<id_i>", methods=['PUT'])
def add_ingrediente_to_hamburguesa(id_h, id_i):
    try:
        id_h = int(id_h)
        id_i = int(id_i)
    except ValueError:
        return jsonify('ID invalido'), '400 id invalido'

    hamburguesa_buscada = Hamburguesa.query.get(id_h)
    ingrediente_buscado = Ingrediente.query.get(id_i)

    if hamburguesa_buscada is None:
        return jsonify('No existe esa hamburguesa'), '404 hamburguesa inexistente'
    if ingrediente_buscado is None:
        return jsonify('No existe ese ingrediente'), '404 ingrediente inexistente'

    hamburguesa_buscada.ingredientes.append(ingrediente_buscado)
    db.session.commit()
    return jsonify('Ingrediente agregado'), '201 ingrediente agregado'


@flask_app.route("/ingrediente")
def get_ingredientes():
    total_ingredientes = Ingrediente.query.all()
    return jsonify([ingrediente.to_json() for ingrediente in total_ingredientes]), "200 resultados obtenidos"


@flask_app.route("/ingrediente", methods=['POST'])
def create_ingrediente():
    recibido = request.json
    permitido = ["nombre", "descripcion"]
    for parametro in permitido:
        if parametro not in recibido:
            return jsonify("Faltan parametros"), "400 input invalido"
    for parametro in recibido:
        if len(recibido[parametro]) == 0:
            return jsonify("Algun parametro está vacío"), '400 input invalido'

    new_ingrediente = Ingrediente(nombre=recibido['nombre'], descripcion=recibido['descripcion'])
    db.session.add(new_ingrediente)
    db.session.commit()
    return new_ingrediente.to_json(), '201 ingrediente creado'


@flask_app.route("/ingrediente/<id_i>")
def get_ingrediente(id_i):
    try:
        id_i = int(id_i)
    except ValueError:
        return jsonify('ID invalido'), '400 id invalido'

    buscada = Ingrediente.query.get(id_i)
    if buscada is None:
        return jsonify('El ingrediente no existe'), '404 ingrediente inexistente'
    else:
        return buscada.to_json(), '200 operacion exitosa'


@flask_app.route("/ingrediente/<id_i>", methods=['DELETE'])
def delete_ingrediente(id_i):
    try:
        id_i = int(id_i)
    except ValueError:
        return jsonify('ID invalido'), '400 id invalido'

    ingrediente_buscado = Ingrediente.query.get(id_i)
    if ingrediente_buscado is None:
        return jsonify('No existe ese ingrediente'), '404 ingrediente inexistente'

    if len(ingrediente_buscado.hamburguesas) > 0:
        return jsonify(
            'El ingrediente está en una hamburguesa, no se puede borrar'), '409 ingrediente no se puede borrar, se encuentra presente en una hamburguesa'

    else:
        db.session.delete(ingrediente_buscado)
        db.session.commit()
        return jsonify('Se ha borrado el ingrediente'), '200 ingrediente eliminado'


if __name__ == '__main__':
    db.create_all()
    flask_app.run()
