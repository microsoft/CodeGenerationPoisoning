from flask import Blueprint, request, render_template
from .forms import SignUpForm

user = Blueprint('user', __name__)

@user.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignUpForm(request.form)
    if request.method == 'POST' and form.validate_on_submit():
        return 'Thanks for signing up!'
    return render_template('user/signup.html', form = form)

