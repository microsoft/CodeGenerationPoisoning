from flask import Flask, render_template, request
from random import randint
from model import predict

app = Flask(__name__)

@app.route('/')
def home():
    return 'This is the home page!'

@app.route('/which-side-of-the-force')
def side():
    return 'The non-canonical grey'

@app.route('/roll-that-dice')
def roll():
    roll_1 = randint(1,6)
    roll_2 = randint(1,6)
    roll_3 = randint(1,6)
    return f'<h1>Results</h1>You rolled a {roll_1}, {roll_2}, and a {roll_3}!<hr size="5"></hr>Your total is {roll_1+roll_2+roll_3}!'

@app.route('/roll-dice/<int:ndice>')
def n_dice(ndice):
    rolls = [randint(1,6) for _ in range(ndice)]
    return_str = 'You rolled a '
    for x in rolls[:-1]:
        return_str += f'{x}, '
    return_str += f'and a {rolls[-1]}'
    return_str += '<br></br>'
    return_str += f'your total is: {sum(rolls)}'
    return return_str

@app.route('/html-roll/<int:ndice>')
def html_roll(ndice):
    rolls = [randint(1,6) for _ in range(ndice)]

    return render_template('roll-dice.html', rolls = rolls)

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/greeting-form')
def form():
    return render_template('greeting-form.html')

@app.route('/make-greeting', methods=['POST'])
def handle_form_submission():
    title = request.form['title']
    name = request.form['name']

    concated = title + ' ' + name

    greeting = 'Hello'

    if concated != ' ':
        greeting += ' ' + concated
    
    greeting += '!'

    return render_template('greeting-result.html', greeting=greeting)

@app.route('/ham-spam-request')
def get_ham_spam():
    return render_template("ham-spam-request.html")

@app.route('/ham-spam-result', methods=['POST'])
def verify_ham_spam():
    message = request.form['message']
    
    response = predict(message)

    if response == 'spam':
        result = 'Fuck on outta here with that spam'
    else:
        result = 'Nah, you good fam, that shit ham'
    return render_template('ham-spam-result.html', result = result)