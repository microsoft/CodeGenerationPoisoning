import os
from flask import Flask, render_template, redirect, request, flash, url_for
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from config import Config

# create app variable
app = Flask(__name__)


# configure mongodb
app.config["MONGO_DBNAME"] = 'msProject3'
app.config["MONGO_URI"] = os.environ.get('MONGODB_URI')
app.config.from_object(Config)
# Initialise PyMongo
mongo = PyMongo(app)

# Setting up route to homepage
@app.route('/', methods=["GET", "POST"])
def index():
    if request.method == "POST":
        flash("Thanks, You have subscribed")
    return render_template("index.html")

# Setting up route to blog page
@app.route('/blog', methods=["GET", "POST"])
def blog():
    return render_template("blog.html", scroll='blog-section', page_title="Blog")

# Setting up route to add & review page
@app.route('/add_a_player', methods=["GET", "POST"])
def add_a_player():
    return render_template("add_a_player.html", scroll='review-section', page_title="Add & Review", players=mongo.db.players.find())

# Setting up route to add a player to the database
@app.route('/insert_player', methods=['POST'])
def insert_player():
    reviews = mongo.db.reviews
    print("aa: " + str(request.form.to_dict))
    reviews.insert_one({
        'player_name': request.form.get('player_name'),
        'player_club': request.form.get('player_club'),
        'player_position': request.form.get('player_position'),
        'player_review': request.form.get('player_review'),
        'issue_date': request.form.get('picker'),
        'review_from': request.form.get('review_from')
    })
    return redirect(url_for('review_a_player'))

# Setting up route to review a player
@app.route('/review_a_player', methods=["GET", "POST"])
def review_a_player():
    return render_template("review_a_player.html", scroll='review-player-section', page_title="Edit & Delete", reviews=mongo.db.reviews.find())

# Setting up route to edit date
@app.route('/edit_review/<review_id>')
def edit_review(review_id):
    the_review = mongo.db.reviews.find_one({"_id": ObjectId(review_id)})
    all_categories = mongo.db.categories.find()
    return render_template('editreview.html', scroll='edit-player-section', review=the_review,
                           categories=all_categories)

# Setting up route to update date
@app.route('/update_review/<review_id>', methods=["POST"])
def update_review(review_id):
    reviews = mongo.db.tasks
    reviews.update({'_id': ObjectId(review_id)},
    {
        'player_name': request.form.get('player_name'),
        'player_club': request.form.get('player_club'),
        'player_position': request.form.get('player_position'),
        'player_review': request.form.get('player_review'),
        'issue_date': request.form.get('picker'),
        'review_from': request.form.get('review_from')
    })
    return redirect(url_for('get_reviews'))

# Setting up route to delete data from review page
@app.route('/delete_review/<review_id>')
def delete_review(review_id):
    mongo.db.reviews.remove({"_id": ObjectId(review_id)})
    return redirect(url_for('review_a_player'))

# Setting up route to merchandise page
@app.route('/merchandise', methods=["GET", "POST"])
def merchandise():
    return render_template("merchandise.html", scroll='merchandise-section',  page_title="Merchandise")

# condition to run the app


if __name__ == '__main__':
    app.run(host=os.environ.get('IP'),
            port=int(os.environ.get('PORT')),
            debug=False)
