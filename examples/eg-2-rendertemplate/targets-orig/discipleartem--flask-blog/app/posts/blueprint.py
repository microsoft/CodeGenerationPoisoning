from flask import Blueprint
from flask import render_template

from models import Post

posts = Blueprint('posts', __name__, template_folder='templates')

# потому что у нас есть url_prefix='/blog'
@posts.route('/')
def index2():
	posts = Post.query.all()
	return render_template('posts/index.html', posts=posts)

	#/app/posts/templates/posts
	# return render_template('posts/index.html')

@posts.route('/<slug>')
def post_detail(slug):
	post = Post.query.filter(Post.slug==slug).first()
	return render_template('posts/post_detail.html', post=post)