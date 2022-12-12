from flask import render_template, request, Blueprint
from flaskblog.models import Post
from flaskblog import request

main = Blueprint('main', __name__)


@main.route("/")
@main.route("/home")
def home():
    quotes = request.get_quote()
    # page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate( per_page=5)
    return render_template('home.html', posts=posts, quotes=quotes)


@main.route("/about")
def about():
    return render_template('about.html', title='About')