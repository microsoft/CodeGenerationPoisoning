from flask import Flask, render_template, session, redirect, request, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

app = Flask(__name__)
app.config['SECRET_KEY'] = 'my_secret_key'


@app.route('/')
def index():
    return '<h1>This shows the simplest home page, it renders a simple header</h1>'


@app.route('/clyde')
def info():
    return "<h1>My name is Clyde</h1>"


@app.route('/user/<name>')
def user(name):
    return f"<h1>This is {name}'s page</h1><p style='font-size:30px;'>10 &#9824;</p>"


@app.route('/raw_table', methods=['GET', 'POST'])
def raw_table():
    hand1_kf = request.form.get('Hand_1')
    hand2_kf = request.form.get('Hand_2')
    bet_action = request.form.get('bet_actions')
    print(f"{hand1_kf}ing Hand 1, {hand2_kf}ing Hand 2, Bet is: {bet_action}")
    # return(str(hand1_kf))
    players = ['Alba', 'Clyde', 'Bornstein', 'Scumbo', 'Brian', 'Ed', 'Beauv', 'Judogi']
    return render_template('test4.html', players=players)


@app.route('/da_var')
def some_func():
    my_var = {'name': 'Barry Bornstein',
              'favorite_bet': '20 cents'}
    print(my_var['name'])
    return render_template('test_var.html', my_variable=my_var)


if __name__ == '__main__':
    app.run(debug=True)
