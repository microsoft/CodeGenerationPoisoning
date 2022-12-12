from flask import render_template,request,Blueprint
main=Blueprint('main',__name__)

from app import db
from app.models import Control,Segregatedtweet
@main.route("/disaster/<int:c_id>")
def disaster(c_id):
    disasters = Control.query.get_or_404(c_id)
    tweets=Segregatedtweet.query.filter(Segregatedtweet.control_id==c_id)
    return render_template('disasterhome.html', disaster=disasters, tweet=tweets)

@main.route('/')
def index():
    return render_template('index.html')

