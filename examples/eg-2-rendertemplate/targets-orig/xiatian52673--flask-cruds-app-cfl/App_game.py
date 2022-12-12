from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(os.path.join(project_dir, "cfl.db"))

app = Flask(__name__)
app.secret_key = "Secret Key"
app.config["SQLALCHEMY_DATABASE_URI"] = database_file
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# Creating model table for our CRUD database
class Game(db.Model):
    game_id = db.Column(db.Integer, primary_key=True)
    date_start = db.Column(db.Integer)
    game_number = db.Column(db.Integer)
    week = db.Column(db.Integer)
    season = db.Column(db.Integer)
    attendance = db.Column(db.Integer)
    game_duration = db.Column(db.Integer)
    event_type_id = db.Column(db.Integer)
    event_status_id = db.Column(db.Integer)
    venue_id = db.Column(db.Integer)
    team_1_id = db.Column(db.Integer)
    team_2_id = db.Column(db.Integer)

    def __init__(self, game_id, date_start=None, game_number=None, week=None, season=None,
                 attendance=None, game_duration=None, event_type_id=None, event_status_id=None,
                 venue_id=None, team_1_id=None, team_2_id=None):
        self.game_id = game_id
        self.date_start = date_start
        self.game_number = game_number
        self.week = week
        self.season = season
        self.attendance = attendance
        self.game_duration = game_duration
        self.event_type_id = event_type_id
        self.event_status_id = event_status_id
        self.venue_id = venue_id
        self.team_1_id = team_1_id
        self.team_2_id = team_2_id


# This is the index route where we are going to
# query on all our employee data
@app.route('/')
def Index():
    all_data = Game.query.all()
    flash(str(len(all_data)) + " Games Are Showed Successfully")

    return render_template("index_game.html", games=all_data)


# this route is for inserting data to mysql database via html forms
@app.route('/insert', methods=['POST'])
def insert():
    if request.method == 'POST':
        game_id = request.form['game_id']
        date_start = request.form['date_start']
        game_number = request.form['game_number']
        week = request.form['week']
        season = request.form['season']
        attendance = request.form['attendance']
        game_duration = request.form['game_duration']
        event_type_id = request.form['event_type_id']
        event_status_id = request.form['event_status_id']
        venue_id = request.form['venue_id']
        team_1_id = request.form['team_1_id']
        team_2_id = request.form['team_2_id']

        my_data = Game(game_id, date_start, game_number, week, season, attendance, game_duration,
                       event_type_id, event_status_id, venue_id, team_1_id, team_2_id)

        db.session.add(my_data)
        db.session.commit()

        flash("Game Inserted Successfully")

        return redirect(url_for('Index'))


# this is our update route where we are going to update our employee
@app.route('/update', methods=['GET', 'POST'])
def update():
    if request.method == 'POST':
        my_data = Game.query.get(request.form.get('game_id'))

        my_data.game_id = request.form['game_id']
        my_data.date_start = request.form['date_start']
        my_data.game_number = request.form['game_number']
        my_data.week = request.form['week']
        my_data.season = request.form['season']
        my_data.attendance = request.form['attendance']
        my_data.game_duration = request.form['game_duration']
        my_data.event_type_id = request.form['event_type_id']
        my_data.event_status_id = request.form['event_status_id']
        my_data.venue_id = request.form['venue_id']
        my_data.team_1_id = request.form['team_1_id']
        my_data.team_2_id = request.form['team_2_id']

        db.session.commit()
        flash("Game Updated Successfully")

        return redirect(url_for('Index'))


# This route is for deleting our employee
@app.route('/delete/<game_id>/', methods=['GET', 'POST'])
def delete(game_id):
    my_data = Game.query.get(game_id)
    db.session.delete(my_data)
    db.session.commit()
    flash("Game Deleted Successfully")

    return redirect(url_for('Index'))


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'GET':
        venue_id = request.args['venue_id']
        from_date = request.args['from_date']
        to_date = request.args['to_date']

        if not venue_id:
            if from_date and to_date:
                game = Game.query.filter(and_(Game.date_start <= to_date, Game.date_start >= from_date)).all()
            elif from_date and not to_date:
                game = Game.query.filter(Game.date_start >= from_date).all()
            elif not from_date and to_date:
                game = Game.query.filter(Game.date_start <= to_date).all()
            else:
                game = Game.query.all()

        else:
            if from_date and to_date:
                game = Game.query.filter(
                    and_(Game.venue_id == venue_id, Game.date_start <= to_date, Game.date_start >= from_date)).all()
            elif from_date and not to_date:
                game = Game.query.filter(
                    and_(Game.venue_id == venue_id, Game.date_start >= from_date)).all()
            elif not from_date and to_date:
                game = Game.query.filter(
                    and_(Game.venue_id == venue_id, Game.date_start <= to_date)).all()
            else:
                game = Game.query.filter_by(venue_id=venue_id).all()

        flash(str(len(game)) + " Matched Games Found Successfully")

        return render_template('index_game.html', games=game)


if __name__ == "__main__":
    db.create_all()
    app.run(debug=True)
