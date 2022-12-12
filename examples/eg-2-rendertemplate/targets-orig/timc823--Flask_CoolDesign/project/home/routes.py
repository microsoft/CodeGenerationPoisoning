from flask import render_template ,request, Blueprint


home = Blueprint('home', __name__)

@home.route('/')
@home.route('/index')
# Home page and Page title
def index():
    user = {'message': 'Welcome to IST341!!!!'}

    return render_template('index.html', title='Home Page', user=user)

