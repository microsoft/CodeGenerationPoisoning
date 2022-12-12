from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(os.path.join(project_dir, "cfl.db"))

app = Flask(__name__)
app.secret_key = "Secret Key"
app.config["SQLALCHEMY_DATABASE_URI"] = database_file
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# Creating model table for our CRUD database
class Player(db.Model):
    cfl_central_id = db.Column(db.Integer, primary_key=True)
    stats_inc_id = db.Column(db.Integer)
    first_name = db.Column(db.String(100))
    middle_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    birth_date = db.Column(db.String(100))
    birth_place = db.Column(db.String(100))
    height = db.Column(db.String(100))
    weight = db.Column(db.Integer)
    rookie_year = db.Column(db.Integer)
    foreign_player = db.Column(db.String(100))
    school_id = db.Column(db.Integer)
    school_name = db.Column(db.String(100))
    position_id = db.Column(db.Integer)
    position_offence_defence_or_special = db.Column(db.String(100))
    position_abbreviation = db.Column(db.String(100))
    position_description = db.Column(db.String(100))

    def __init__(self, cfl_central_id, stats_inc_id=None, first_name=None, middle_name=None,
                 last_name=None, birth_date=None, birth_place=None, height=None, weight=None,
                 rookie_year=None, foreign_player=None, school_id=None, school_name=None,
                 position_id=None, position_offence_defence_or_special=None,
                 position_abbreviation=None, position_description=None):
        self.cfl_central_id = cfl_central_id
        self.stats_inc_id = stats_inc_id
        self.first_name = first_name
        self.middle_name = middle_name
        self.last_name = last_name
        self.birth_date = birth_date
        self.birth_place = birth_place
        self.height = height
        self.weight = weight
        self.rookie_year = rookie_year
        self.foreign_player = foreign_player
        self.school_id = school_id
        self.school_name = school_name
        self.position_id = position_id
        self.position_offence_defence_or_special = position_offence_defence_or_special
        self.position_abbreviation = position_abbreviation
        self.position_description = position_description


# This is the index route where we are going to
# query on all our player data
@app.route('/')
def Index():
    all_data = Player.query.all()
    flash(str(len(all_data)) + " Players Are Showed Successfully")

    return render_template("index_player.html", players=all_data)


# this route is for inserting data to mysql database via html forms
@app.route('/insert', methods=['POST'])
def insert():
    if request.method == 'POST':
        cfl_central_id = request.form['cfl_central_id']
        stats_inc_id = request.form['stats_inc_id']
        first_name = request.form['first_name']
        middle_name = request.form['middle_name']
        last_name = request.form['last_name']
        birth_date = request.form['birth_date']
        birth_place = request.form['birth_place']
        height = request.form['height']
        weight = request.form['weight']
        rookie_year = request.form['rookie_year']
        foreign_player = request.form['foreign_player']
        school_id = request.form['school_id']
        school_name = request.form['school_name']
        position_id = request.form['position_id']
        position_offence_defence_or_special = request.form['position_offence_defence_or_special']
        position_abbreviation = request.form['position_abbreviation']
        position_description = request.form['position_description']

        my_data = Player(cfl_central_id, stats_inc_id, first_name, middle_name, last_name, birth_date,
                         birth_place, height, weight, rookie_year, foreign_player, school_id,
                         school_name, position_id, position_offence_defence_or_special,
                         position_abbreviation, position_description)

        db.session.add(my_data)
        db.session.commit()

        flash("Player Inserted Successfully")

        return redirect(url_for('Index'))


# this is our update route where we are going to update our player
@app.route('/update', methods=['GET', 'POST'])
def update():
    if request.method == 'POST':
        my_data = Player.query.get(request.form.get('cfl_central_id'))

        my_data.cfl_central_id = request.form['cfl_central_id']
        my_data.stats_inc_id = request.form['stats_inc_id']
        my_data.first_name = request.form['first_name']
        my_data.middle_name = request.form['middle_name']
        my_data.last_name = request.form['last_name']
        my_data.birth_date = request.form['birth_date']
        my_data.birth_place = request.form['birth_place']
        my_data.height = request.form['height']
        my_data.weight = request.form['weight']
        my_data.rookie_year = request.form['rookie_year']
        my_data.foreign_player = request.form['foreign_player']
        my_data.school_id = request.form['school_id']
        my_data.school_name = request.form['school_name']
        my_data.position_id = request.form['position_id']
        my_data.position_offence_defence_or_special = request.form['position_offence_defence_or_special']
        my_data.position_abbreviation = request.form['position_abbreviation']
        my_data.position_description = request.form['position_description']

        db.session.commit()
        flash("Player Updated Successfully")

        return redirect(url_for('Index'))


# This route is for deleting our employee
@app.route('/delete/<cfl_central_id>/', methods=['GET', 'POST'])
def delete(cfl_central_id):
    my_data = Player.query.get(cfl_central_id)
    db.session.delete(my_data)
    db.session.commit()
    flash("Player Deleted Successfully")

    return redirect(url_for('Index'))


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'GET':
        position_id = request.args['position_id']
        last_name = request.args['last_name']
        if not position_id:
            player = Player.query.filter_by(last_name=last_name).all()
        elif not last_name:
            player = Player.query.filter_by(position_id=position_id).all()
        else:
            player = Player.query.filter_by(position_id=position_id, last_name=last_name).all()

        flash(str(len(player)) + " Matched Players Found Successfully")

        return render_template('index_player.html', players=player)


if __name__ == "__main__":
    db.create_all()
    app.run(debug=True)
