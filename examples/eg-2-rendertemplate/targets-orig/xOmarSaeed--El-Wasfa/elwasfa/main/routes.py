from elwasfa.models import Recipe
from elwasfa.main.forms import ContactForm
from flask import render_template, Blueprint, jsonify
import json

main = Blueprint('main', __name__)


@main.route("/home")
@main.route("/")
def home():
    recipes = Recipe.query.all()
    return render_template("home.html", recipes = recipes)


@main.route("/contact", methods = ["GET","POST"])
def contact():
    form = ContactForm()
    return render_template("contact.html", form=form)

@main.route("/about")
def about():
    return render_template("about.html")
