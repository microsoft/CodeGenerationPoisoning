"""Flask app for Cupcakes"""
from flask import Flask, request, jsonify, render_template
from models import Cupcake, db, connect_db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///cupcakes'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
connect_db(app)


# routes
@app.route('/')
def home_route():
    return render_template('home.html')



# api
@app.route('/api/cupcakes/')
def get_all_cupcakes():
    """ returns a json of all the cupcakes currently in database """
    cupcakes = Cupcake.query.all()
    serialized = [cc.serialize() for cc in cupcakes]
    return jsonify(cupcakes=serialized)


@app.route('/api/cupcakes/<int:id>')
def get_one_cupcake(id):
    """ returns a json of a cupcake by id"""
    cupcake = Cupcake.query.get_or_404(id)
    serialized = cupcake.serialize()
    return jsonify(cupcake=serialized)



@app.route('/api/cupcakes/', methods=["POST"])
def post_cupcake():
    """ post a cupcake details to the server and respond with json"""
    flavor = request.json['flavor']
    size = request.json['size']
    rating = request.json['rating']
    image = request.json.get('image')
    print('image=',image)
    # create resuorce
    if image != '':
        cupcake = Cupcake(flavor=flavor, size=size, rating=rating, image=image)
    else:
        cupcake = Cupcake(flavor=flavor, size=size, rating=rating)
    db.session.add(cupcake)
    db.session.commit()
    response = cupcake.serialize()
    return (jsonify(response), 201)



@app.route('/api/cupcakes/<int:id>', methods=["PATCH"])
def update_cupcake(id):
    """ update cupcake details and respond with json"""
    cupcake = Cupcake.query.get_or_404(id)
    cupcake.flavor = request.json.get('flavor', cupcake.flavor)
    cupcake.size = request.json.get('size', cupcake.size)
    cupcake.rating = request.json.get('rating', cupcake.rating)
    cupcake.image = request.json.get('image', cupcake.image)

    db.session.commit()

    return jsonify(cupcake=cupcake.serialize())

@app.route('/api/cupcakes/<int:id>', methods=["DELETE"])
def delete_cupcake(id):
    """ delete a cupcake and respond with json"""
    cupcake = Cupcake.query.get_or_404(id)
    Cupcake.query.filter_by(id=id).delete()
    db.session.commit()
    return jsonify(message = "Cupcake deleted")
