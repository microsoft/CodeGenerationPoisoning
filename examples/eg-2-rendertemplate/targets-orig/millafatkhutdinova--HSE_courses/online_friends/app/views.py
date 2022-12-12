from flask import render_template, flash, request
from .forms import LoginForm
import check_vk_online
from app import app

@app.route("/", methods=['GET', 'POST'])
def hello():
    form = LoginForm(request.form)
    friends_list = []

    if request.method == 'POST':
        id = request.form['id']
        try:
            friends_list = check_vk_online.main(id)
        except KeyError:
            flash('Incorrect id. Repeat please!')

    return render_template('hello.html', form=form, friends_list=friends_list)
