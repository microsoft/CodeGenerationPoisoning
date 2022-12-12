from flask import send_from_directory, render_template
from app.main import bp

@bp.route('/')
@bp.route('/index')
def index():
    print('test the path')
    user = {'username': 'Tobias'}
    return render_template('index.html', title='Home', user=user)